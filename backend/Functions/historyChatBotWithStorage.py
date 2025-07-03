# historyChatBotWithStorage.py
import os
from dotenv import load_dotenv
from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime
import uuid
from bson.objectid import ObjectId
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import HumanMessage, AIMessage

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure

# Import the vector_store from vector_db.py
# This assumes vector_db.py correctly initializes `vector_store`
from Functions.Helpers.vector_db import vector_store

load_dotenv()

# --- Environment Variables ---
MONGO_URI = os.getenv("MONGODB_URI")
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

if not MONGO_URI:
    raise ValueError("MONGODB_URI not set in .env file for historyChatBotWithStorage.")
if not GOOGLE_CLOUD_PROJECT:
    raise ValueError("GOOGLE_CLOUD_PROJECT not set in .env file for historyChatBotWithStorage.")

# --- MongoDB Connection ---
mongo_client = None
db = None
chat_sessions_collection = None

try:
    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client["youtube_notebook"]
    notebooks_collection = db["notebooks"]
    chat_sessions_collection = db["chat_sessions"] # New collection for chat sessions
    # Ensure index on session_id for faster lookups
    chat_sessions_collection.create_index("session_id", unique=True)
    print(f"Connected to MongoDB database: {db.name} (from historyChatBotWithStorage.py)")
except (ConnectionFailure, OperationFailure) as e:
    print(f"MongoDB connection failed in historyChatBotWithStorage.py: {e}")
    mongo_client = None
    db = None
    chat_sessions_collection = None


# --- Initialize Generative AI Model for Chatbot Responses ---
llm_chat_history = None
try:
    llm_chat_history = ChatVertexAI(
        model_name="gemini-2.0-flash", # Using gemini-2.0-flash for faster responses
        temperature=0.5, # Slightly higher temperature than factual chatBot for more conversational feel
        project=GOOGLE_CLOUD_PROJECT,
        location=GOOGLE_CLOUD_LOCATION,
    )
    print(f"Chatbot LLM with history ({llm_chat_history.model_name}) initialized in historyChatBotWithStorage.py.")
except Exception as e:
    print(f"Error initializing Chatbot LLM with history in historyChatBotWithStorage.py: {e}.")
    print("Please ensure Vertex AI API is enabled for the chosen model in your project and location.")
    llm_chat_history = None


# --- Chat History Truncation Logic ---
MAX_VERBATIM_HISTORY_LENGTH = 6 # Keep this many (user+assistant) turns as verbatim
# This means 3 user messages and 3 AI responses before summarization kicks in.
# For LangChain MessagesPlaceholder, this means 2 * MAX_VERBATIM_HISTORY_LENGTH messages.

def summarize_chat_history(
    history_to_summarize: List[Dict[str, str]]
) -> str:
    """
    Summarizes a given segment of chat history using the LLM.
    """
    if not history_to_summarize:
        return ""
    if llm_chat_history is None:
        print("Warning: LLM not initialized for history summarization.")
        return "Chat history could not be summarized due to LLM error."

    # Convert to LangChain message objects for summarization
    lc_messages_to_summarize = []
    for msg in history_to_summarize:
        if msg["role"] == "user":
            lc_messages_to_summarize.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            lc_messages_to_summarize.append(AIMessage(content=msg["content"]))

    # Prompt for summarization
    summarization_prompt = ChatPromptTemplate.from_messages(
        [
            ("system",
             "You are a helpful assistant whose sole purpose is to concisely summarize "
             "the provided conversation history. Focus on the main topics and key information "
             "discussed, ignoring conversational filler. The summary should be brief and "
             "represent the essential context for continuing the conversation."
            ),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "Please summarize the above conversation history."),
        ]
    )

    summarization_chain = (
        RunnablePassthrough.assign(chat_history=lambda x: lc_messages_to_summarize)
        | summarization_prompt
        | llm_chat_history
        | StrOutputParser()
    )

    try:
        summary = summarization_chain.invoke({"chat_history": lc_messages_to_summarize})
        print(f"History summarized: {summary[:50]}...") # Print first 50 chars of summary
        return summary
    except Exception as e:
        print(f"Error during history summarization: {e}")
        return "Error: Could not summarize previous conversation."


def create_new_chat_session(
    user_id: str,
    notebook_id: str, # ADD THIS PARAMETER
    video_id: Optional[str] = None,
    first_user_prompt: str = ""
) -> str:
    """
    Creates a new chat session in MongoDB and returns its session_id.
    Stores the initial user prompt and links it to a specific notebook.
    """
    if chat_sessions_collection is None:
        raise ConnectionError("MongoDB chat_sessions_collection is not initialized.")
    if notebooks_collection is None: # ADD THIS CHECK
        raise ConnectionError("MongoDB notebooks_collection is not initialized.")

    session_id = str(uuid.uuid4())
    session_data = {
        "session_id": session_id,
        "user_id": user_id,
        "video_id": video_id,
        "notebook_id": notebook_id, # ADD THIS FIELD TO SESSION DATA
        "history": [],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "first_prompt": first_user_prompt
    }
    try:
        chat_sessions_collection.insert_one(session_data)
        print(f"New chat session created: {session_id} for user {user_id}, video {video_id or 'N/A'}, notebook {notebook_id}")

        # ADD THIS BLOCK: Update the notebook document with the new session ID
        notebooks_collection.update_one(
            {"_id": ObjectId(notebook_id)}, # Query by notebook's ObjectId
            {
                "$addToSet": {"session_id_list": session_id}, # Add session_id to the list if not already there
                "$set": {"latest_session_id": session_id, "updated_at": datetime.utcnow()} # Set this as the latest session
            },
            upsert=False # Do not create a new notebook if it doesn't exist
        )
        print(f"Notebook {notebook_id} updated with new latest session: {session_id}")

        return session_id
    except Exception as e:
        print(f"Error creating new chat session or updating notebook: {e}")
        raise # Re-raise the exception for FastAPI to catch

def get_chat_history_from_db(session_id: str) -> List[Dict[str, str]]:
    """
    Retrieves the chat history for a given session_id from MongoDB.
    Returns an empty list if session not found or history is empty.
    """
    if chat_sessions_collection is None:
        raise ConnectionError("MongoDB chat_sessions_collection is not initialized.")

    try:
        session_doc = chat_sessions_collection.find_one({"session_id": session_id})
        if session_doc:
            return session_doc.get("history", [])
        return []
    except Exception as e:
        print(f"Error retrieving chat history for session {session_id}: {e}")
        return [] # Return empty history on error


def update_chat_history_in_db(
    session_id: str,
    user_message: str,
    ai_message: str
):
    """
    Appends a new user message and AI response to the chat history in MongoDB.
    """
    if chat_sessions_collection is None:
        raise ConnectionError("MongoDB chat_sessions_collection is not initialized.")

    try:
        # Append new messages
        chat_sessions_collection.update_one(
            {"session_id": session_id},
            {
                "$push": {
                    "history": {
                        "$each": [
                            {"role": "user", "content": user_message},
                            {"role": "assistant", "content": ai_message}
                        ]
                    }
                },
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        # print(f"Chat history updated for session: {session_id}") # Removed for less verbosity
    except Exception as e:
        print(f"Error updating chat history for session {session_id}: {e}")
        # Consider more robust error handling or retry mechanisms in a production app


def get_history_chatbot_response_with_storage(
    query_text: str,
    session_id: str,
    user_id: str,
    target_video_id: Optional[str] = None
) -> Tuple[str, str]: # NEW: Returns a tuple (AI response, session_id)
    """
    Generates a chatbot response using RAG, incorporating conversation history
    from storage and video context. Updates the history in storage.
    Applies summarization to history passed to LLM if it exceeds MAX_VERBATIM_HISTORY_LENGTH.

    Args:
        query_text (str): The user's current question.
        session_id (str): The ID of the current chat session.
        user_id (str): The ID of the user (defaults to '1').
        target_video_id (Optional[str]): If provided, limits the search to a specific video.

    Returns:
        Tuple[str, str]: The generated answer from the chatbot and the session ID.
    """
    if llm_chat_history is None:
        return "Error: Chatbot LLM with history is not initialized.", session_id
    if vector_store is None:
        return "Error: Vector store is not initialized. Cannot retrieve context.", session_id
    if chat_sessions_collection is None:
        return "Error: MongoDB chat_sessions_collection is not initialized.", session_id
    
    # 1. Retrieve existing chat history from DB
    raw_chat_history = get_chat_history_from_db(session_id)

    # 2. Apply truncation/summarization logic to history for LLM context
    # raw_chat_history contains {"role": "user/assistant", "content": "..."}
    # It has 2 entries per turn (user, assistant).
    num_turns_in_history = len(raw_chat_history) // 2

    lc_chat_history_for_llm: List[AIMessage | HumanMessage] = []

    if num_turns_in_history > MAX_VERBATIM_HISTORY_LENGTH:
        # Determine the number of messages to summarize
        messages_to_summarize = raw_chat_history[:-MAX_VERBATIM_HISTORY_LENGTH * 2]
        recent_messages = raw_chat_history[-MAX_VERBATIM_HISTORY_LENGTH * 2:]

        summary_content = summarize_chat_history(messages_to_summarize)
        if summary_content:
            lc_chat_history_for_llm.append(AIMessage(content=f"Previous conversation summary: {summary_content}"))
        else:
            # Fallback if summarization failed, just add older messages directly (might exceed tokens)
            print("Warning: Summarization failed, adding older messages directly to history for LLM.")
            for msg in messages_to_summarize:
                if msg["role"] == "user":
                    lc_chat_history_for_llm.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    lc_chat_history_for_llm.append(AIMessage(content=msg["content"]))

        # Add recent messages verbatim
        for msg in recent_messages:
            if msg["role"] == "user":
                lc_chat_history_for_llm.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                lc_chat_history_for_llm.append(AIMessage(content=msg["content"]))
        
        print(f"History truncated. Original turns: {num_turns_in_history}, LLM input messages: {len(lc_chat_history_for_llm)}")

    else:
        # No summarization needed, use full history
        for msg in raw_chat_history:
            if msg["role"] == "user":
                lc_chat_history_for_llm.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                lc_chat_history_for_llm.append(AIMessage(content=msg["content"]))
        print(f"History not truncated. Total turns: {num_turns_in_history}")


    # 3. Retrieval: Configure the retriever based on whether a specific video ID is provided
    if target_video_id:
        # print(f"History Chatbot (Storage): Performing retrieval for query '{query_text}' on video ID: {target_video_id}") # Removed for less verbosity
        retriever = vector_store.as_retriever(
            search_kwargs={"k": 5, "pre_filter": {"video_id": target_video_id}}
        )
    else:
        # print(f"History Chatbot (Storage): Performing retrieval for query '{query_text}' across all videos.") # Removed for less verbosity
        retriever = vector_store.as_retriever(
            search_kwargs={"k": 5}
        )

    # Helper function to format retrieved documents for the LLM prompt
    def format_docs(docs):
        if not docs:
            return "No relevant video context found."
        return "\n\n".join(doc.page_content for doc in docs)

    # 4. Generation (RAG Chain with History): Define the LangChain RAG pipeline
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system",
             "You are a helpful assistant for YouTube video content. "
             "Use the following retrieved video transcript excerpts AND "
             "the conversation history to answer the user's question. "
             "If you don't know the answer based on the provided context, "
             "politely state that you cannot find the answer in the given information. "
             "You can make up answers but explicity mention that this is out of video information. Be concise but informative."
            ),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "Context: {context}\nQuestion: {question}"),
        ]
    )

    rag_chain = (
        RunnablePassthrough.assign(
            context=lambda x: format_docs(retriever.invoke(x["question"])),
            chat_history=lambda x: lc_chat_history_for_llm # Use the potentially truncated history
        )
        | prompt
        | llm_chat_history
        | StrOutputParser()
    )

    try:
        # Invoke the RAG chain
        ai_response = rag_chain.invoke({"question": query_text})

        # 5. Update chat history in DB (always save full turn for persistence)
        update_chat_history_in_db(session_id, query_text, ai_response)

        return ai_response, session_id # NEW: Return session_id
    except Exception as e:
        print(f"Error during RAG chain invocation in historyChatBotWithStorage.py: {e}")
        return f"Error generating response: {e}", session_id
    

def get_chat_session_summary(session_id: str) -> Optional[Dict]:
    """
    Retrieves a summary (first prompt, creation date, and notebook ID) for a given session ID.
    """
    if chat_sessions_collection is None:
        print("Warning: MongoDB chat_sessions_collection is not initialized for summary.")
        return None
    try:
        session_doc = chat_sessions_collection.find_one(
            {"session_id": session_id},
            {"session_id": 1, "first_prompt": 1, "created_at": 1, "notebook_id": 1} # ADDED "notebook_id": 1
        )
        if session_doc:
            return {
                "session_id": session_doc["session_id"],
                "first_prompt": session_doc.get("first_prompt", "New Chat Session"),
                "created_at": session_doc["created_at"].isoformat(),
                "notebook_id": session_doc.get("notebook_id", None) # ADDED notebook_id
            }
        return None
    except Exception as e:
        print(f"Error retrieving chat session summary for {session_id}: {e}")
        return None

def get_notebook_chat_sessions_summaries(session_ids: List[str]) -> List[Dict]:
    """
    Retrieves summaries for a list of chat session IDs.
    This function expects to receive the list of session_ids from main.py,
    which gets them from the notebook document.
    """
    summaries = []
    for s_id in session_ids:
        summary = get_chat_session_summary(s_id)
        if summary:
            summaries.append(summary)
    # Sort by created_at, most recent first
    summaries.sort(key=lambda x: x["created_at"], reverse=True)
    return summaries    
    






