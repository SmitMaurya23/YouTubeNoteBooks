# timeStampDecider.py
import os
from dotenv import load_dotenv
from typing import List, Dict, Optional
import sys

# Import vector_store and embeddings_model
from backend.Helpers.vector_db import vector_store, embeddings_model

# Import LangChain components
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_google_vertexai import ChatVertexAI

load_dotenv()

# --- Environment Variables for Vertex AI ---
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

if not GOOGLE_CLOUD_PROJECT:
    print("Error: GOOGLE_CLOUD_PROJECT not set in .env file for timestamp LLM.", file=sys.stderr)
    raise ValueError("GOOGLE_CLOUD_PROJECT not set in .env file.")
if not GOOGLE_CLOUD_LOCATION:
    print("Error: GOOGLE_CLOUD_LOCATION not set in .env file for timestamp LLM.", file=sys.stderr)
    raise ValueError("GOOGLE_CLOUD_LOCATION not set in .env file.")

# --- Initialize Generative AI Model for Timestamp Refinement ---
# Use ChatVertexAI consistent with chatBot.py
llm_timestamp = None
try:
    llm_timestamp = ChatVertexAI(
        model_name="gemini-2.0-flash", # Consistent model name
        temperature=0.1, # Lower temperature for very precise, factual timestamp extraction
        project=GOOGLE_CLOUD_PROJECT,
        location=GOOGLE_CLOUD_LOCATION,
    )
    print(f"Timestamp LLM ({llm_timestamp.model_name}) initialized in timeStampDecider.py.")
except Exception as e:
    print(f"Error initializing Timestamp LLM in timeStampDecider.py: {e}.")
    print("Please ensure Vertex AI API is enabled for the chosen model in your project and location.")
    llm_timestamp = None # Set to None if initialization fails

def format_timestamp(seconds: float) -> str:
    """Converts seconds into a human-readable HH:MM:SS or MM:SS format."""
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours:02}:{minutes:02}:{seconds:02}"
    return f"{minutes:02}:{seconds:02}"

async def get_timestamps_for_topic(query_text: str, video_id: str, k: int = 5) -> List[Dict]:
    """
    Retrieves the most relevant timestamps for a given topic in a video using RAG.

    Args:
        query_text: The user's query (topic or instance).
        video_id: The ID of the YouTube video.
        k: The number of top relevant chunks to retrieve from the vector store.

    Returns:
        A list of dictionaries, each containing 'timestamp' (formatted string)
        and 'text' (the relevant transcript snippet).
    """
    if llm_timestamp is None:
        print("Error: Timestamp LLM is not initialized. Cannot refine timestamps.", file=sys.stderr)
        return []
    if not vector_store:
        print("Error: Vector store not initialized. Cannot retrieve timestamps.", file=sys.stderr)
        return []
    if not embeddings_model:
        print("Error: Embeddings model not initialized. Cannot retrieve timestamps.", file=sys.stderr)
        return []

    print(f"Searching for timestamps for query: '{query_text}' in video: {video_id}")

    try:
        # 1. Retrieval: Configure the retriever to filter by video_id
        retriever = vector_store.as_retriever(
            search_kwargs={"k": k, "pre_filter": {"video_id": video_id}}
        )

        # Helper function to format retrieved documents for the LLM prompt
        def format_docs_for_timestamp_llm(docs):
            if not docs:
                return "No relevant context found."
            formatted_segments = []
            for i, doc in enumerate(docs):
                if 'start' in doc.metadata and 'end' in doc.metadata:
                    start_time = doc.metadata['start']
                    formatted_segments.append(
                        f"- Timestamp: {format_timestamp(start_time)}\n"
                        f"  Text: \"{doc.page_content}\""
                    )
                else:
                    print(f"Warning: Chunk {i} missing 'start' or 'end' metadata. Skipping for LLM context. Metadata: {doc.metadata}")
            return "\n".join(formatted_segments)

        # 2. Generation (RAG Chain for Timestamp Extraction):
        # Define the prompt for the LLM to extract precise timestamps.
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", 
                 "You are an expert assistant at extracting precise timestamps from video transcripts. "
                 "Given the user's query and relevant transcript segments with their timestamps, "
                 "identify the most precise start time (HH:MM:SS or MM:SS) where the topic "
                 "'{query}' is discussed. Provide only the timestamp and a very brief (1-2 sentences) "
                 "snippet of the text that directly relates to that timestamp. "
                 "If the topic is not clearly present in the provided context, state that you cannot find it. "
                 "Do not make up answers or timestamps.\n\n"
                 "Transcript Segments:\n{context}\n\n"
                 "Format your answer as: `Timestamp: HH:MM:SS - \"Relevant snippet...\"`\n"
                 "Example: `Timestamp: 01:23 - \"This is where the topic is introduced.\"`\n"
                 "If multiple timestamps are relevant, provide the top 3 most relevant, each on a new line."
                ),
                ("user", "Query: {query}"),
            ]
        )

        # Construct the RAG chain for timestamp extraction
        timestamp_rag_chain = (
            {"context": retriever | format_docs_for_timestamp_llm, "query": RunnablePassthrough()}
            | prompt
            | llm_timestamp
            | StrOutputParser()
        )

        # Invoke the RAG chain
        response_text = timestamp_rag_chain.invoke(query_text)
        print(f"LLM Raw Response for Timestamps:\n{response_text}")

        # Parse LLM's response
        parsed_timestamps = []
        for line in response_text.split('\n'):
            line = line.strip()
            if line.startswith("Timestamp:"):
                try:
                    parts = line.split(" - ", 1)
                    if len(parts) == 2:
                        timestamp_str = parts[0].replace("Timestamp:", "").strip()
                        snippet = parts[1].strip().strip('"')
                        parsed_timestamps.append({
                            "timestamp": timestamp_str,
                            "text": snippet
                        })
                except Exception as e:
                    print(f"Error parsing LLM response line '{line}': {e}", file=sys.stderr)
        
        if not parsed_timestamps:
            print("LLM did not return timestamps in the expected format or found no relevant timestamps. Attempting fallback.", file=sys.stderr)
            # Fallback if LLM doesn't return in expected format or finds nothing
            # Retrieve directly from the vector store and use the first result's timestamp
            query_results_fallback = vector_store.similarity_search(
                query=query_text,
                k=1, # Get only the top result for fallback
                search_kwargs={"pre_filter": {"video_id": video_id}}
            )
            if query_results_fallback and 'start' in query_results_fallback[0].metadata:
                top_doc = query_results_fallback[0]
                parsed_timestamps.append({
                    "timestamp": format_timestamp(top_doc.metadata['start']),
                    "text": top_doc.page_content[:150] + "..." # Provide a snippet
                })
                print(f"Fallback: Used timestamp from top retrieved chunk: {parsed_timestamps[0]['timestamp']}")
            else:
                print("Fallback also failed to find a timestamp.", file=sys.stderr)

        return parsed_timestamps

    except Exception as e:
        print(f"Error in get_timestamps_for_topic: {e}", file=sys.stderr)
        return []

if __name__ == "__main__":
    print("--- Testing timeStampDecider.py ---")
    test_video_id = "eWiBLgxOcW0" # Replace with an actual video ID in your DB
    test_query = "In which part of the video, its mentioned that Innovation is exception in india while its a system in South Korea." # Replace with a query relevant to your test video

    if test_video_id == "YOUR_TEST_VIDEO_ID_HERE" or test_query == "YOUR_TOPIC_OR_INSTANCE_QUERY_HERE":
        print("\n*** Please update 'test_video_id' and 'test_query' in timeStampDecider.py for proper testing. ***")
        print("Make sure you have processed a video and its transcript is embedded in your MongoDB Atlas.")
    else:
        import asyncio
        async def run_test():
            print(f"Attempting to find timestamps for '{test_query}' in video '{test_video_id}'...")
            timestamps = await get_timestamps_for_topic(test_query, test_video_id)
            if timestamps:
                print("\nFound Timestamps:")
                for ts in timestamps:
                    print(f"- {ts['timestamp']}: \"{ts['text']}\"")
            else:
                print("No timestamps found.")

        asyncio.run(run_test())
