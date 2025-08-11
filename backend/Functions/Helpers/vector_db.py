
# backend/vector_db.py
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from langchain_mongodb.vectorstores import MongoDBAtlasVectorSearch
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings # Import the base Embeddings class
from typing import List, Dict

# NEW IMPORTS FOR EXPLICIT AUTHENTICATION
import json
import tempfile
import traceback # For detailed error logging

# Import native Vertex AI SDK components
import vertexai
from vertexai.language_models import TextEmbeddingModel, TextEmbeddingInput

load_dotenv()

# Define your Google Cloud Project ID and Region
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1") # Default to us-central1 if not set

if not GOOGLE_CLOUD_PROJECT:
    raise ValueError("GOOGLE_CLOUD_PROJECT not set in .env file.")
if not GOOGLE_CLOUD_LOCATION:
    raise ValueError("GOOGLE_CLOUD_LOCATION not set in .env file.")

# --- NEW BLOCK: Explicitly handle GOOGLE_APPLICATION_CREDENTIALS for Render ---
# This block reads the service account key JSON content from an environment variable,
# writes it to a temporary file, and then sets the GOOGLE_APPLICATION_CREDENTIALS
# environment variable to point to this file. This forces the Vertex AI SDK to
# use these specific credentials for authentication, bypassing potential implicit
# authentication issues in deployment environments.
service_account_json_content = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
if service_account_json_content:
    try:
        # tempfile.NamedTemporaryFile creates a unique file and ensures it's cleaned up
        # We set delete=False initially because we need the file to exist after the 'with' block
        # The file will be cleaned up on process exit or when manually unlinked.
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as temp_creds_file:
            temp_creds_file.write(service_account_json_content)
            temp_creds_path = temp_creds_file.name
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_creds_path
        print(f"GOOGLE_APPLICATION_CREDENTIALS set to temporary file: {temp_creds_path}")
    except Exception as e:
        print(f"Error writing temporary credentials file: {e}")
        # We don't re-raise here to allow the process to continue and potentially
        # fall back to implicit authentication, though that's what we're trying to fix.
else:
    print("GOOGLE_APPLICATION_CREDENTIALS_JSON environment variable not found. Relying on implicit authentication.")

# Initialize Vertex AI for the session
try:
    # This vertexai.init will now prioritize the GOOGLE_APPLICATION_CREDENTIALS
    # environment variable if it has been successfully set in the new block above.
    vertexai.init(project=GOOGLE_CLOUD_PROJECT, location=GOOGLE_CLOUD_LOCATION)
    print(f"Vertex AI initialized for project: {GOOGLE_CLOUD_PROJECT}, location: {GOOGLE_CLOUD_LOCATION}")
except Exception as e:
    print(f"Error initializing Vertex AI SDK: {e}")
    raise # Re-raise to stop execution if Vertex AI cannot be initialized

# --- Custom Embedding Class using Native Vertex AI SDK ---
class VertexAIEmbeddingsNative(Embeddings):
    """Custom Embedding class that uses the native vertexai SDK."""

    def __init__(self, model_name: str = "gemini-embedding-001"):
        self.model_name = model_name
        self.client = None
        try:
            # This will use the authenticated context set by vertexai.init(),
            # which now (hopefully) includes the explicit service account credentials.
            self.client = TextEmbeddingModel.from_pretrained(self.model_name)
            print(f"Native Vertex AI TextEmbeddingModel '{self.model_name}' loaded successfully.")
        except Exception as e:
            # NEW: Print full traceback for better debugging on deployment logs
            traceback.print_exc()
            raise ValueError(f"Failed to load native Vertex AI embedding model '{self.model_name}': {e}")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts by sending them one by one."""
        embeddings_list = []
        for i, text in enumerate(texts):
            try:
                if self.client is None:
                    raise RuntimeError("TextEmbeddingModel client is not initialized.")
                # Send one text at a time as per the API's batchSize=1 requirement
                input_obj = TextEmbeddingInput(text, task_type="RETRIEVAL_DOCUMENT")
                response = self.client.get_embeddings([input_obj]) # Pass a list with a single input
                embeddings_list.append(list(response[0].values))
                # Optional: Add a small delay to respect rate limits if needed for many requests
                # time.sleep(0.05) # 50ms delay
            except Exception as e:
                print(f"Error embedding document {i+1}/{len(texts)}: '{text[:50]}...': {e}")
                # Decide how to handle errors for individual chunks (e.g., skip, re-raise, log)
                embeddings_list.append([]) # Append an empty list or None to indicate failure for this chunk
        return embeddings_list
    def embed_query(self, text: str) -> list[float]:
        """Embed a single query text."""
        if self.client is None:
            raise RuntimeError("TextEmbeddingModel client is not initialized.")
        input_obj = TextEmbeddingInput(text, task_type="RETRIEVAL_QUERY")
        embeddings = self.client.get_embeddings([input_obj]) # Still a single input
        return list(embeddings[0].values)

# --- Initialize MongoDB Client ---
MONGO_URI = os.getenv("MONGODB_URI")
DB_NAME = "youtube_notebook"
COLLECTION_NAME = "video_embeddings" # A new collection specifically for embeddings
INDEX_NAME = "vector_index" # The name of your Atlas Vector Search Index

if not MONGO_URI:
    raise ValueError("MONGODB_URI not set in .env file.")

try:
    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client[DB_NAME]
    embeddings_collection = db[COLLECTION_NAME]
    print(f"Connected to MongoDB database: {DB_NAME}, collection: {COLLECTION_NAME}")
except Exception as e:
    print(f"Error connecting to MongoDB for vector store: {e}")
    mongo_client = None
    embeddings_collection = None

# --- Initialize Custom Embeddings Model ---
embeddings_model = None
try:
    embeddings_model = VertexAIEmbeddingsNative(model_name="gemini-embedding-001")
    # Verify dimension after initialization
    test_embedding_dim = len(embeddings_model.embed_query("test"))
    print(f"Embeddings model initialized successfully. Embedding dimension: {test_embedding_dim}")
    if test_embedding_dim != 3072:
        raise ValueError(f"Expected embedding dimension 3072 from 'gemini-embedding-001', but got {test_embedding_dim}.")
except ValueError as e:
    print(f"Error initializing custom embeddings model: {e}")
    embeddings_model = None


# --- Initialize MongoDB Atlas Vector Search ---
vector_store = None
if embeddings_collection is not None and embeddings_model is not None:
    try:
        vector_store = MongoDBAtlasVectorSearch(
            collection=embeddings_collection,
            embedding=embeddings_model, # Pass our custom embeddings_model here
            index_name=INDEX_NAME, # This must match the name of your index in Atlas
            text_key="text", # The field in your MongoDB document that holds the raw text
            embedding_key="embedding", # The field in your MongoDB document that holds the vector
            relevance_score_fn="cosine" # Must match your Atlas index
        )
        print("MongoDBAtlasVectorSearch initialized successfully.")
    except Exception as e:
        print(f"Error initializing MongoDBAtlasVectorSearch: {e}")
        vector_store = None

# --- Text Splitter for Chunking Transcripts ---
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000, # Max characters per chunk
    chunk_overlap=200, # Overlap to maintain context between chunks
    length_function=len,
    is_separator_regex=False,
)

def embed_and_store_transcript(video_id: str, transcript_list: List[Dict]) -> bool:
    """
    Chunks the transcript using a text splitter, aggregates timestamps for each chunk,
    generates embeddings, and stores them in MongoDB Atlas.

    Args:
        video_id: The ID of the YouTube video.
        transcript_list: The list of transcript entries from utils.fetch_transcript,
                               e.g., [{"text": "...", "start": 0.0, "duration": 5.0}, ...]
    """
    if not vector_store:
        print("Vector store not initialized. Cannot embed and store transcript.")
        return False
    if not transcript_list:
        print(f"No transcript list provided for video ID: {video_id}. Skipping embedding.")
        return False

    print(f"Preparing chunks for video_id: {video_id} with timestamp metadata...")

    # 1. Create a single long string of the transcript and map original segment positions
    full_transcript_text = ""
    # This list will store (original_text, start_time, end_time, char_start_index, char_end_index)
    original_segments_info = []
    current_char_index = 0

    for entry in transcript_list:
        segment_text = entry.get("text", "")
        segment_start = entry.get("start", 0.0)
        segment_duration = entry.get("duration", 0.0)
        segment_end = segment_start + segment_duration

        original_segments_info.append(
            (segment_text, segment_start, segment_end, current_char_index, current_char_index + len(segment_text))
        )
        full_transcript_text += segment_text + " " # Add a space for separation
        current_char_index += len(segment_text) + 1 # +1 for the space

    # 2. Use the RecursiveCharacterTextSplitter on the full transcript text
    # This will return a list of strings (the chunks)
    text_chunks = text_splitter.split_text(full_transcript_text)

    final_documents_for_embedding = []

    # 3. For each new chunk, find its aggregated start and end timestamp
    for chunk_content in text_chunks:
        # Find the character start and end index of this chunk within the full_transcript_text
        # This is a simplified way; a more robust way would be to use the splitter's
        # `create_documents` method if it provided character offsets in metadata,
        # or to manually track. For `split_text`, we need to find the chunk's position.
        # This assumes unique chunk content or careful handling of duplicates.
        # A safer approach for character position:
        try:
            chunk_char_start = full_transcript_text.index(chunk_content)
            chunk_char_end = chunk_char_start + len(chunk_content)
        except ValueError:
            # If chunk_content is not found directly (e.g., due to overlap or special chars),
            # this method might fail. A more robust solution would involve iterating through
            # the original text and tracking offsets.
            print(f"Warning: Could not find chunk content in full transcript. Skipping chunk: {chunk_content[:50]}...")
            continue

        min_start_time = float('inf')
        max_end_time = float('-inf')
        found_overlap = False

        # Iterate through original segments to find overlaps and aggregate timestamps
        for original_text, original_start, original_end, original_char_start, original_char_end in original_segments_info:
            # Check for overlap between the chunk's character range and the original segment's character range
            # An overlap exists if:
            # (chunk_start < original_end_char AND chunk_end > original_start_char)
            if max(chunk_char_start, original_char_start) < min(chunk_char_end, original_char_end):
                min_start_time = min(min_start_time, original_start)
                max_end_time = max(max_end_time, original_end)
                found_overlap = True

        if found_overlap and min_start_time != float('inf') and max_end_time != float('-inf'):
            # Create a Document for the new, larger chunk with aggregated timestamps
            doc = Document(
                page_content=chunk_content,
                metadata={
                    "video_id": video_id,
                    "source": f"youtube_transcript_{video_id}",
                    "start": min_start_time,
                    "end": max_end_time,
                    "duration": max_end_time - min_start_time # Calculate duration for convenience
                }
            )
            final_documents_for_embedding.append(doc)
        else:
            print(f"Warning: No timestamp overlap found for chunk: {chunk_content[:50]}... Skipping.")


    print(f"Created {len(final_documents_for_embedding)} larger, context-rich chunks for video_id: {video_id}.")

    # Add documents to vector store
    try:
        # MongoDBAtlasVectorSearch.add_documents uses the 'embedding' object provided
        vector_store.add_documents(documents=final_documents_for_embedding)
        print(f"Successfully embedded and stored {len(final_documents_for_embedding)} chunks for video_id: {video_id}")
        return True
    except Exception as e:
        print(f"Error embedding and storing chunks for video_id {video_id}: {e}")
        return False

if __name__ == "__main__":
    # Example Usage for testing this module
    print("\n--- Testing vector_db.py module ---")
    sample_video_id = "test_video_123_chunked" # Use a unique ID for testing
    # A sample transcript list with timestamps
    sample_transcript_list = [
        {"text": "This is the first part of a sample transcript for testing.", "start": 0.0, "duration": 5.0},
        {"text": "It needs to be long enough to demonstrate how the RecursiveCharacterTextSplitter works.", "start": 5.5, "duration": 7.0},
        {"text": "Each chunk will then be embedded using the native Vertex AI model and stored in MongoDB Atlas.", "start": 13.0, "duration": 8.0},
        {"text": "We expect to see 3072-dimensional embeddings for these combined chunks.", "start": 21.5, "duration": 6.5},
        {"text": "The task type for embedding documents is set to RETRIEVAL_DOCUMENT and for queries to RETRIEVAL_QUERY.", "start": 28.0, "duration": 9.0},
        {"text": "This setup ensures consistency with how the model should be used for RAG purposes.", "start": 37.5, "duration": 7.5},
        {"text": "Let's see if this direct approach successfully bypasses previous issues.", "start": 45.0, "duration": 6.0},
        {"text": "If this works, it confirms that the native SDK is indeed the reliable path for embeddings in your specific environment.", "start": 51.5, "duration": 10.0},
        {"text": "This final part concludes our sample transcript for testing the chunking and embedding process.", "start": 62.0, "duration": 8.0},
    ] * 5 # Repeat to make it longer and ensure chunking occurs

    print(f"Attempting to embed and store sample transcript for video ID: {sample_video_id}")
    success = embed_and_store_transcript(sample_video_id, sample_transcript_list)
    if success:
        print("Sample transcript processed successfully.")

        print("\nAttempting a similarity search (should find the sample text)")
        if vector_store:
            try:
                query_results = vector_store.similarity_search(
                    query="How does the text splitting and embedding process work?",
                    k=2,
                    filter={"video_id": sample_video_id} # Filter by the test video ID
                )
                print("Similarity search results:")
                for doc in query_results:
                    print(f"- Content: {doc.page_content[:100]}...")
                    print(f"  Metadata: {doc.metadata}")
                    if 'start' in doc.metadata and 'end' in doc.metadata:
                        print(f"  Time Range: {doc.metadata['start']} - {doc.metadata['end']} seconds")
            except Exception as e:
                print(f"Error during similarity search: {e}")
        else:
            print("Vector store not initialized for search.")
    else:
        print("Failed to process sample transcript.")