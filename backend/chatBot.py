# chatBot.py
import os
from dotenv import load_dotenv
from typing import Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_google_vertexai import ChatVertexAI

# Import the vector_store from vector_db.py
# This assumes vector_db.py correctly initializes `vector_store`
# using the VertexAIEmbeddingsNative class.
from vector_db import vector_store

load_dotenv()

# --- Environment Variables for Vertex AI ---
# These should be consistent with main.py and vector_db.py
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

if not GOOGLE_CLOUD_PROJECT:
    raise ValueError("GOOGLE_CLOUD_PROJECT not set in .env file for chatbot.")
# GOOGLE_CLOUD_LOCATION is optional, defaults to us-central1

# --- Initialize Generative AI Model for Chatbot Responses ---
llm_chat = None
try:
    llm_chat = ChatVertexAI(
        # Corrected model name: removed the asterisk.
        # 'gemini-1.5-flash-001' is a common stable version.
        # If this still fails, try 'gemini-1.0-pro-001' as a reliable fallback.
        model_name="gemini-2.0-flash", # Corrected model name
        temperature=0.3, # Lower temperature for more factual answers
        project=GOOGLE_CLOUD_PROJECT,
        location=GOOGLE_CLOUD_LOCATION,
    )
    print(f"Chatbot LLM ({llm_chat.model_name}) initialized in chatBot.py.")
except Exception as e:
    print(f"Error initializing Chatbot LLM in chatBot.py: {e}.")
    print("Please ensure Vertex AI API is enabled for the chosen model in your project and location.")
    llm_chat = None # Set to None if initialization fails

def get_chatbot_response(query_text: str, target_video_id: Optional[str] = None) -> str:
    """
    Generates a chatbot response using RAG based on the provided query and video context.

    Args:
        query_text (str): The user's question.
        target_video_id (Optional[str]): If provided, limits the search to a specific video.

    Returns:
        str: The generated answer from the chatbot.
    """
    if llm_chat is None:
        return "Error: Chatbot LLM is not initialized."
    if vector_store is None:
        return "Error: Vector store is not initialized. Cannot retrieve context."

    # 1. Retrieval: Configure the retriever based on whether a specific video ID is provided
    # Changed 'filter' to 'pre_filter' for MongoDBAtlasVectorSearch search_kwargs
    if target_video_id:
        print(f"Chatbot: Performing retrieval for query '{query_text}' on video ID: {target_video_id}")
        retriever = vector_store.as_retriever(
            search_kwargs={"k": 5, "pre_filter": {"video_id": target_video_id}} # Changed 'filter' to 'pre_filter'
        )
    else:
        print(f"Chatbot: Performing retrieval for query '{query_text}' across all videos.")
        retriever = vector_store.as_retriever(
            search_kwargs={"k": 5} # Retrieve top 5 chunks from all indexed videos
        )

    # Helper function to format retrieved documents for the LLM prompt
    def format_docs(docs):
        if not docs:
            return "No relevant context found."
        # Join the page_content of each document, separated by double newlines
        return "\n\n".join(doc.page_content for doc in docs)

    # 2. Generation (RAG Chain): Define the LangChain RAG pipeline
    # The prompt guides the LLM to use the provided context.
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are a helpful assistant for YouTube video content. Use the following retrieved video transcript excerpts to answer the user's question. If you don't know the answer based on the provided context, politely state that you cannot find the answer in the given information. Do not make up answers."),
            ("user", "Context: {context}\nQuestion: {question}"),
        ]
    )

    # Construct the RAG chain:
    # - "context": The retriever gets documents, and format_docs formats them.
    # - "question": The user's original query is passed through.
    # - These are then fed into the prompt.
    # - The LLM generates a response.
    # - StrOutputParser converts the LLM's output message to a string.
    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm_chat
        | StrOutputParser()
    )

    try:
        # Invoke the RAG chain with the user's query
        response = rag_chain.invoke(query_text)
        return response
    except Exception as e:
        print(f"Error during RAG chain invocation in chatBot.py: {e}")
        return f"Error generating response: {e}"

# This __name__ == "__main__" block is for testing chatBot.py independently if needed
if __name__ == "__main__":
    print("--- Testing chatBot.py module ---")
    # This test assumes vector_db.py has been run and populated the vector store
    # with 'test_video_123' or other video data.

    # Example 1: Chat with a specific video
    sample_video_id_for_chat = "test_video_123" # Replace with an actual video ID in your DB
    sample_query_specific = "What is the primary focus of this video?"
    print(f"\nQuerying specific video '{sample_video_id_for_chat}': '{sample_query_specific}'")
    response_specific = get_chatbot_response(sample_query_specific, sample_video_id_for_chat)
    print(f"Chatbot Response (Specific Video): {response_specific}")

    # Example 2: Chat across all videos (if you have multiple indexed)
    sample_query_general = "Tell me about text splitting."
    print(f"\nQuerying generally: '{sample_query_general}'")
    response_general = get_chatbot_response(sample_query_general)
    print(f"Chatbot Response (General): {response_general}")

