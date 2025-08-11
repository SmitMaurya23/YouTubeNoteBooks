import os
from  pymongo import MongoClient
from langchain_mongodb.vectorstores import MongoDBAtlasVectorSearch
from langchain_core.documents import Document
from typing import List,Optional
from app.core.settings import settings

class VectorRepository:
    """
    Handles all direct interactions with the MongoDB Atlas Vector Search.
    This class is responsible for the low-level data access for the vector database.
    """

    def __init__(self, vector_store: MongoDBAtlasVectorSearch):
        self.vector_store=vector_store

    def add_documents_list(self, documents: List[Document])->None:
        # internally using embed_documents that we defined in embeddings.py
        """
        Adds a list of documents to the vector store.
        """
        try:
            self.vector_store.add_documents(documents=documents)
            print(f"Successfully embedded and stored {len(documents)}chunks.")
        except Exception as e:
            print(f"Error embedding and storing chunks: {e}")
            raise

    def similarity_search_query(self, query: str, k: int, filter: Optional[dict] = None) -> List[Document]:
        """
        Performs a similarity search in the vector store with an optional filter.
        """
        try:
            # Pass all arguments directly, mimicking the monolithic code's behavior
            results = self.vector_store.similarity_search(query,k,filter)
            return results
        except Exception as e:
            print(f"Error during similarity search: {e}")
            raise # Re-raise to preserve the original traceback