# historyChatBotWithStorage.py
import os
from dotenv import load_dotenv
from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime
import uuid

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import HumanMessage, AIMessage

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure

# Import the vector_store from vector_db.py
# This assumes vector_db.py correctly initializes `vector_store`
from vector_db import vector_store

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


def create_new_chat_session(user_id: str = "1", video_id: Optional[str] = None) -> str:
    """
    Creates a new chat session in MongoDB and returns its session_id.
    """
    if chat_sessions_collection is None:
        raise ConnectionError("MongoDB chat_sessions_collection is not initialized.")

    session_id = str(uuid.uuid4())
    session_data = {
        "session_id": session_id,
        "user_id": user_id,
        "video_id": video_id, # Can be None for general chats
        "history": [], # Stores messages as {"role": "user/assistant", "content": "..."}
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    try:
        chat_sessions_collection.insert_one(session_data)
        print(f"New chat session created: {session_id} for user {user_id}")
        return session_id
    except Exception as e:
        print(f"Error creating new chat session: {e}")
        raise

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
    user_id: str = "1", # Default user_id
    target_video_id: Optional[str] = None
) -> str:
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
        str: The generated answer from the chatbot.
    """
    if llm_chat_history is None:
        return "Error: Chatbot LLM with history is not initialized."
    if vector_store is None:
        return "Error: Vector store is not initialized. Cannot retrieve context."
    if chat_sessions_collection is None:
        return "Error: MongoDB chat_sessions_collection is not initialized."

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
             "Do not make up answers. Be concise but informative."
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

        return ai_response
    except Exception as e:
        print(f"Error during RAG chain invocation in historyChatBotWithStorage.py: {e}")
        return f"Error generating response: {e}"

# This __name__ == "__main__" block is for testing historyChatBotWithStorage.py independently
if __name__ == "__main__":
    print("--- Testing historyChatBotWithStorage.py module (Terminal Chat with Storage and Truncation) ---")
    print("Type 'exit' to end the chat.")

    default_user_id = "terminal_user_1"
    
    # !!! IMPORTANT !!!
    # Replace this with an actual video ID that has been processed and embedded
    # via your FastAPI '/transcript/{video_id}' endpoint.
    # If you don't have one, the chatbot will only rely on general knowledge (if any)
    # or will state it can't find info.
    test_video_id = "eWiBLgxOcW0" # <--- REPLACE WITH A REAL VIDEO ID FROM YOUR DB

    # --- Test 1: Chatting with a specific video context and new session ---
    print(f"\n--- Starting NEW chat session about video ID: {test_video_id} ---")
    print("Please ensure this video ID has its transcript embedded in your vector DB.")
    try:
        current_session_id = create_new_chat_session(user_id=default_user_id, video_id=test_video_id)
        print(f"New session ID: {current_session_id}")
    except Exception as e:
        print(f"Failed to create new session: {e}. Exiting.")
        exit()

    print(f"Chat will summarize history after {MAX_VERBATIM_HISTORY_LENGTH} turns (user+AI pairs).")
    turn_count = 0
    while True:
        user_input = input(f"You (Turn {turn_count+1}, Specific Video, New Session): ")
        if user_input.lower() == 'exit':
            break

        ai_response = get_history_chatbot_response_with_storage(
            user_input, current_session_id, default_user_id, test_video_id
        )
        print(f"AI (Turn {turn_count+1}, Specific Video, New Session): {ai_response}")
        turn_count += 1
    
    # --- Test 2: Resuming an existing chat session (if you still have the ID) ---
    print("\n--- Resuming an existing chat session (if you have an ID) ---")
    resume_session_id = input(f"Enter an existing session ID to resume (or press Enter to skip): ").strip()

    if resume_session_id:
        print(f"Attempting to resume session: {resume_session_id}")
        if chat_sessions_collection is None:
            print("Error: MongoDB chat_sessions_collection is not initialized. Cannot resume session.")
        else:
            session_doc = chat_sessions_collection.find_one({"session_id": resume_session_id})
            if session_doc:
                resumed_video_id = session_doc.get("video_id")
                print(f"Resumed session is linked to video ID: {resumed_video_id}")
                resumed_turn_count = len(session_doc.get("history", [])) // 2
                print(f"Resumed session has {resumed_turn_count} existing turns.")

                while True:
                    user_input = input(f"You (Resumed Session, Turn {resumed_turn_count + 1}): ")
                    if user_input.lower() == 'exit':
                        break
                    ai_response = get_history_chatbot_response_with_storage(
                        user_input, resume_session_id, default_user_id, resumed_video_id
                    )
                    print(f"AI (Resumed Session, Turn {resumed_turn_count + 1}): {ai_response}")
                    resumed_turn_count += 1
            else:
                print(f"Session ID '{resume_session_id}' not found. Skipping resume test.")
    else:
        print("Skipping resume session test.")

    print("Chat session ended.")