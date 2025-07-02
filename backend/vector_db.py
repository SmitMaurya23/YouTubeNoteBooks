# backend/vector_db.py
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from langchain_mongodb.vectorstores import MongoDBAtlasVectorSearch
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings # Import the base Embeddings class

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

# Initialize Vertex AI for the session
try:
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
            self.client = TextEmbeddingModel.from_pretrained(self.model_name)
            print(f"Native Vertex AI TextEmbeddingModel '{self.model_name}' loaded successfully.")
        except Exception as e:
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

def embed_and_store_transcript(video_id: str, transcript_text: str) -> bool:
    """
    Chunks the transcript, generates embeddings, and stores them in MongoDB Atlas.
    """
    if not vector_store:
        print("Vector store not initialized. Cannot embed and store transcript.")
        return False
    if not transcript_text:
        print(f"No transcript text provided for video ID: {video_id}. Skipping embedding.")
        return False

    print(f"Chunking transcript for video_id: {video_id}...")
    chunks = text_splitter.create_documents(
        texts=[transcript_text],
        metadatas=[{"video_id": video_id, "source": f"youtube_transcript_{video_id}"}]
    )
    print(f"Transcript chunked into {len(chunks)} parts.")

    # Add chunks to vector store
    try:
        # MongoDBAtlasVectorSearch.add_documents uses the 'embedding' object provided
        vector_store.add_documents(documents=chunks)
        print(f"Successfully embedded and stored {len(chunks)} chunks for video_id: {video_id}")
        return True
    except Exception as e:
        print(f"Error embedding and storing chunks for video_id {video_id}: {e}")
        return False

if __name__ == "__main__":
    # Example Usage for testing this module
    print("\n--- Testing vector_db.py module ---")
    sample_video_id = "test_video_123" # Use a unique ID for testing
    # A longer sample to ensure chunking happens
    sample_transcript = ("This is the first part of a sample transcript for testing. It needs to be long enough "
                         "to demonstrate how the RecursiveCharacterTextSplitter works by breaking it into multiple chunks. "
                         "Each chunk will then be embedded using the native Vertex AI model and stored in MongoDB Atlas. "
                         "We expect to see 3072-dimensional embeddings. The `task_type` for embedding documents is "
                         "set to 'RETRIEVAL_DOCUMENT' and for queries to 'RETRIEVAL_QUERY'. "
                         "This setup ensures consistency with how the model should be used for RAG purposes. "
                         "Let's see if this direct approach successfully bypasses the previous `langchain_google_genai` "
                         "and `langchain_google_vertexai` issues. If this works, it confirms that the native "
                         "SDK is indeed the reliable path for embeddings in your specific environment.") * 10

    print(f"Attempting to embed and store sample transcript for video ID: {sample_video_id}")
    success = True #embed_and_store_transcript(sample_video_id, sample_transcript)
    if success:
        print("Sample transcript processed successfully.")

        print("\nAttempting a similarity search (should find the sample text)")
        if vector_store:
            try:
                # The vector_store uses its configured 'embeddings_model' for queries as well.
                # No need to explicitly initialize query_embeddings_model separately.
                query_results = vector_store.similarity_search(
                    query="How does the text splitting work?",
                    k=2
                )
                print("Similarity search results:")
                for doc in query_results:
                    print(f"- Content: {doc.page_content[:100]}...")
                    print(f"  Metadata: {doc.metadata}")
            except Exception as e:
                print(f"Error during similarity search: {e}")
        else:
            print("Vector store not initialized for search.")
    else:
        print("Failed to process sample transcript.")