import os
import vertexai
from langchain_google_vertexai import ChatVertexAI
from app.core.settings import settings
from app.services.genai_service import GenAIService
from fastapi import Depends
from langchain_mongodb import MongoDBAtlasVectorSearch
from app.core.embeddings import VertexAIEmbeddingsNative
from app.repositories.vector_repository import VectorRepository
from app.services.youtube_service import YouTubeService
from app.services.vector_service import VectorService
from app.services.transcript_processing_service import TranscriptProcessingService
from app.services.timestamp_service import TimestampService
from pymongo import MongoClient
from app.repositories.chat_mongodb_repository import ChatMongoDBRepository
from app.services.chat_rag_service import ChatRAGService
from app.services.persistant_chat_rag_service import PersistentChatRAGService
from app.services.rag_service import BasicRAGService
from app.repositories.video_mongodb_repository import VideoMongoDBRepository
from app.repositories.user_mongodb_repository import UserMongoDBRepository
from app.repositories.notebook_mongodb_repository import NotebookMongoDBRepository
from app.services.notebook_service import NotebookService



"""
The reason we are using global variables for caching (_embeddings_model_cache, _vector_store_cache, etc.) is to implement the singleton pattern for our dependencies.

Many of the objects we're creating are "expensive" to initialize. This means they take a significant amount of time or resources to set up.

If we defined the model or vector store inside their respective functions without caching, a new instance would be created every single time that function is called.
"""

_embeddings_model_cache=None
_vector_store_cache=None
_gemini_model_cache=None

def get_gemini_model() -> ChatVertexAI:
    """Initializes and returns a singleton instance of the Gemini LLM."""
    global _gemini_model_cache
    if _gemini_model_cache is None:
        try:
            _gemini_model_cache=ChatVertexAI(
                model_name=settings.GEMINI_DESCRIPTION_MODEL,
                temperature=settings.GEMINI_TEMPERATURE,
                project=settings.GOOGLE_CLOUD_PROJECT,
                location=settings.GOOGLE_CLOUD_LOCATION,
            )

        except Exception as e:
            print(f"Error initializing Gemini LLM: {e}")
            _gemini_model_cache=None
            raise ValueError

    return _gemini_model_cache

def get_genai_service(
        llm: ChatVertexAI = Depends(get_gemini_model)
)->GenAIService:
    """Provides a GenAIService instance with the LLM dependency injected."""
    return GenAIService(llm=llm)


def get_embeddings_model()-> VertexAIEmbeddingsNative:
    """Initializes and returns the MongoDBAtlasVectorSearch instance as a singleton."""

    global _embeddings_model_cache
    if _embeddings_model_cache is None:
        try:
            if(settings.EMBEDDINGS_MODEL_NAME is None):
                raise ValueError
            _embeddings_model_cache=VertexAIEmbeddingsNative(
                model_name=settings.EMBEDDINGS_MODEL_NAME
            )
            test_embedding_dim=len(_embeddings_model_cache.embed_query("test"))
            print(f"Embeddings model initialized Successfully !! \n Embedding dimension: {test_embedding_dim}")

            if test_embedding_dim != 3072:
                raise ValueError(f"Expected dimension 3072, but got{test_embedding_dim}")
        except Exception as e:
            print(f"Error initializing custom embedding model: {e}")
            _embeddings_model_cache=None
            raise

    return _embeddings_model_cache


def get_vector_store()->MongoDBAtlasVectorSearch:

    """Initializes and returns the MongoDBAtlasVectorSearch instance as a singleton."""

    global _vector_store_cache
    if _vector_store_cache is None:
        MONGO_URI=settings.MONGODB_URI
        if not MONGO_URI:
            raise ValueError("MONGO_URI not set !!!")

        try:
            mongo_client=MongoClient(MONGO_URI)
            if(settings.DB_NAME is None):
                raise ValueError("DB_NAME is not set !!!")
            db=mongo_client[settings.DB_NAME]
            if(settings.COLLECTION_NAME is None):
                raise ValueError("COLLECTION_NAME is not set !!!")
            embeddings_collection=db[settings.COLLECTION_NAME]

            embeddings_model = get_embeddings_model()
            if embeddings_model is None:
                raise RuntimeError("Embeddings model is not initialized")

            if(settings.INDEX_NAME is None):
                raise ValueError("INDEX_NAME is not set !!!")

            _vector_store_cache=MongoDBAtlasVectorSearch(
            collection=embeddings_collection,
            embedding=embeddings_model,
            index_name=settings.INDEX_NAME,
            text_key="text",
            embedding_key="embedding",
            relevance_score_fn="cosine"
            )

            print("MongoDBAtlasVectorSearch initialized successfully !!!")

        except Exception as e:
            print(f"Error in initializing MongoDBAtlasVectorSearch: {e}")
            _vector_store_cache=None
            raise

    return _vector_store_cache


def get_vector_repository(
        vector_store: MongoDBAtlasVectorSearch=Depends(get_vector_store)
)->VectorRepository:
    """Provides a VectorRepository instance."""
    return VectorRepository(vector_store)

def get_transcript_processing_service()->TranscriptProcessingService:
    """
    Provides a TranscriptProcessing instance. This service is stateless and doesn't require a singleton cache.
    """
    return TranscriptProcessingService()

def get_vector_service(
        vector_repository: VectorRepository=Depends(get_vector_repository),
        transcript_processing_service: TranscriptProcessingService=Depends(get_transcript_processing_service)
)->VectorService:
    """Provides a Vector Service instance."""
    return VectorService(vector_repository,transcript_processing_service)

def get_youtube_service()-> YouTubeService:
    """Provide a YoutTUbeService instance."""
    return YouTubeService()

def get_llm_timestamp()->ChatVertexAI:
    """Provides a ChatVertexAI model instance for timestamp extraction."""
    llm=ChatVertexAI(
        model_name=settings.TIMESTAMP_LLM_MODEL,
        temperature=settings.TIMESTAMP_TEMPERATURE,
        project=settings.GOOGLE_CLOUD_PROJECT,
        location=settings.GOOGLE_CLOUD_LOCATION,
    )
    return llm

def get_timestamp_service(
        llm_timestamp: ChatVertexAI=Depends(get_llm_timestamp),
        vector_repository: VectorRepository=Depends(get_vector_repository)
)-> TimestampService:
    """Provides a TimestampService instance with its dependencies."""
    return TimestampService(llm=llm_timestamp, vector_repository=vector_repository)

def get_mongo_client()->MongoClient:
    """Provides a MongoClient instance."""
    MONGO_URI=settings.MONGODB_URI
    return MongoClient(MONGO_URI)

def get_chat_mongodb_repository(client: MongoClient=Depends(get_mongo_client))->ChatMongoDBRepository:
    """Provides a MongoDBRepository instance."""
    return ChatMongoDBRepository(client)

def get_basic_rag_service(
        llm: ChatVertexAI=Depends(get_gemini_model),
        vector_store: MongoDBAtlasVectorSearch=Depends(get_vector_store)
)->BasicRAGService:
    """Provides the base RAG service."""
    return BasicRAGService(llm,vector_store)

def get_chat_rag_service(
        llm: ChatVertexAI=Depends(get_gemini_model),
        rag_service: BasicRAGService=Depends(get_basic_rag_service)
)->ChatRAGService:
    """Provides the chat RAG service with history management."""
    return ChatRAGService(llm,rag_service)

def get_persistant_chat_rag_service(
        chat_rag_service: ChatRAGService=Depends(get_chat_rag_service),
        chat_mongo_repo: ChatMongoDBRepository=Depends(get_chat_mongodb_repository)
)->PersistentChatRAGService:
    """Provides the full persistent chat service."""
    return PersistentChatRAGService(chat_rag_service,chat_mongo_repo)

def get_video_mongodb_repository(client: MongoClient=Depends(get_mongo_client))->VideoMongoDBRepository:
    return VideoMongoDBRepository(client)

def get_user_mongodb_repository(client: MongoClient=Depends(get_mongo_client))->UserMongoDBRepository:
    return UserMongoDBRepository(client)

def get_notebook_mongodb_repository(client: MongoClient=Depends(get_mongo_client))->NotebookMongoDBRepository:
    return NotebookMongoDBRepository(client)

def get_notebook_service(user_mongodb_repository:UserMongoDBRepository=Depends(get_user_mongodb_repository), notebook_mongodb_repository: NotebookMongoDBRepository=Depends(get_notebook_mongodb_repository),chat_mongodb_repository=Depends(get_chat_mongodb_repository))->NotebookService:
    return NotebookService(user_mongodb_repository,notebook_mongodb_repository,chat_mongodb_repository)
