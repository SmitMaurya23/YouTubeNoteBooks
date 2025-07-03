# historyChatBot.py
import os
from dotenv import load_dotenv
from typing import Optional, List, Tuple

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import HumanMessage, AIMessage

# Import the vector_store from vector_db.py
# This assumes vector_db.py correctly initializes `vector_store`
from backend.Helpers.vector_db import vector_store

load_dotenv()

# --- Environment Variables for Vertex AI ---
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

if not GOOGLE_CLOUD_PROJECT:
    raise ValueError("GOOGLE_CLOUD_PROJECT not set in .env file for historyChatBot.")

# --- Initialize Generative AI Model for Chatbot Responses ---
llm_chat_history = None
try:
    llm_chat_history = ChatVertexAI(
        model_name="gemini-2.0-flash", # Using gemini-2.0-flash for faster responses
        temperature=0.5, # Slightly higher temperature than factual chatBot for more conversational feel
        project=GOOGLE_CLOUD_PROJECT,
        location=GOOGLE_CLOUD_LOCATION,
    )
    print(f"Chatbot LLM with history ({llm_chat_history.model_name}) initialized in historyChatBot.py.")
except Exception as e:
    print(f"Error initializing Chatbot LLM with history in historyChatBot.py: {e}.")
    print("Please ensure Vertex AI API is enabled for the chosen model in your project and location.")
    llm_chat_history = None # Set to None if initialization fails


def get_history_chatbot_response(
    query_text: str,
    chat_history: List[Tuple[str, str]], # Expects a list of (human_message, ai_message) tuples
    target_video_id: Optional[str] = None
) -> str:
    """
    Generates a chatbot response using RAG, incorporating conversation history
    and video context.

    Args:
        query_text (str): The user's current question.
        chat_history (List[Tuple[str, str]]): A list of past (HumanMessage, AIMessage) tuples.
        target_video_id (Optional[str]): If provided, limits the search to a specific video.

    Returns:
        str: The generated answer from the chatbot.
    """
    if llm_chat_history is None:
        return "Error: Chatbot LLM with history is not initialized."
    if vector_store is None:
        return "Error: Vector store is not initialized. Cannot retrieve context."

    # Convert chat_history to LangChain message objects
    # This format is often expected by LangChain's conversational chains
    lc_chat_history = []
    for human_msg, ai_msg in chat_history:
        lc_chat_history.append(HumanMessage(content=human_msg))
        lc_chat_history.append(AIMessage(content=ai_msg))

    # 1. Retrieval: Configure the retriever based on whether a specific video ID is provided
    if target_video_id:
        print(f"History Chatbot: Performing retrieval for query '{query_text}' on video ID: {target_video_id}")
        retriever = vector_store.as_retriever(
            search_kwargs={"k": 5, "pre_filter": {"video_id": target_video_id}}
        )
    else:
        print(f"History Chatbot: Performing retrieval for query '{query_text}' across all videos.")
        retriever = vector_store.as_retriever(
            search_kwargs={"k": 5}
        )

    # Helper function to format retrieved documents for the LLM prompt
    def format_docs(docs):
        if not docs:
            return "No relevant video context found."
        return "\n\n".join(doc.page_content for doc in docs)

    # 2. Generation (RAG Chain with History): Define the LangChain RAG pipeline
    # We use MessagesPlaceholder to inject dynamic chat history into the prompt
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
            MessagesPlaceholder(variable_name="chat_history"), # Placeholder for previous messages
            ("user", "Context: {context}\nQuestion: {question}"),
        ]
    )

    # Construct the RAG chain:
    # - "context": The retriever gets documents, and format_docs formats them.
    # - "question": The user's original query is passed through.
    # - "chat_history": The LangChain message objects of the history.
    rag_chain = (
        RunnablePassthrough.assign(
            context=lambda x: format_docs(retriever.invoke(x["question"])),
            chat_history=lambda x: lc_chat_history # Pass the converted history directly
        )
        | prompt
        | llm_chat_history
        | StrOutputParser()
    )

    try:
        # Invoke the RAG chain with the user's query and the chat history
        response = rag_chain.invoke({"question": query_text})
        return response
    except Exception as e:
        print(f"Error during RAG chain invocation in historyChatBot.py: {e}")
        return f"Error generating response: {e}"

# This __name__ == "__main__" block is for testing historyChatBot.py independently
if __name__ == "__main__":
    print("--- Testing historyChatBot.py module (Terminal Chat) ---")
    print("Type 'exit' to end the chat.")

    # Initialize an empty chat history for the session
    current_chat_history: List[Tuple[str, str]] = []
    
    # !!! IMPORTANT !!!
    # Replace this with an actual video ID that has been processed and embedded
    # via your FastAPI '/transcript/{video_id}' endpoint.
    # If you don't have one, the chatbot will only rely on general knowledge (if any)
    # or will state it can't find info.
    test_video_id = "lVnKTVuCRYo" # <--- REPLACE WITH A REAL VIDEO ID FROM YOUR DB

    # --- Test 1: Chatting with a specific video context ---
    print(f"\n--- Chatting about video ID: {test_video_id} ---")
    print("Please ensure this video ID has its transcript embedded in your vector DB.")
    current_chat_history = [] # Reset history for new conversation
    while True:
        user_input = input("You (Specific Video): ")
        if user_input.lower() == 'exit':
            break

        # Get response using the history and specific video ID
        ai_response = get_history_chatbot_response(user_input, current_chat_history, test_video_id)
        print(f"AI (Specific Video): {ai_response}")

        # Update chat history with the current turn
        current_chat_history.append((user_input, ai_response))
    
    # --- Test 2: Chatting generally (without specific video context) ---
    print("\n--- Chatting Generally (across all videos if indexed) ---")
    print("This will search across all embedded videos or rely on general LLM knowledge.")
    current_chat_history = [] # Reset history for new conversation
    while True:
        user_input = input("You (General): ")
        if user_input.lower() == 'exit':
            break

        # Get response without a specific video ID
        ai_response = get_history_chatbot_response(user_input, current_chat_history, None)
        print(f"AI (General): {ai_response}")

        # Update chat history with the current turn
        current_chat_history.append((user_input, ai_response))

    print("Chat session ended.")