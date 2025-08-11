import traceback
import vertexai
from langchain_core.embeddings import Embeddings
from typing import List
from vertexai.language_models import TextEmbeddingModel, TextEmbeddingInput

class VertexAIEmbeddingsNative(Embeddings):
    """
    Custom Embedding class that uses the native vertexai SDK.
    This class handles the logic for interacting with the Vertex AI embedding model.
    """

    def __init__(self, model_name: str="gemini-embedding-001"):
        self.model_name=model_name
        self.client=None

        try:
            self.client = TextEmbeddingModel.from_pretrained(self.model_name)
            print(f"Native Vertex AI TextEmbeddingModel {self.model_name} loaded successfully!!")
        except Exception as e:
            traceback.print_exc()
            raise ValueError(f"Failed to load native Vertex AI embedding model {self.model_name} : {e}")

    def embed_documents(self, texts: list[str])->list[list[float]]:
        """Embeds a list of texts one by one"""
        embeddings_list=[]
        for i, text in enumerate(texts):
            try:
                if self.client is None:
                    raise RuntimeError("TextEmbeddingModel client is not initialized.")
                input_obj=TextEmbeddingInput(text, task_type="RETRIEVAL_DOCUMENT")
                response=self.client.get_embeddings([input_obj])
                embeddings_list.append(list(response[0].values))
            except Exception as e:
                print(f"Error embedding document {i+1}/{len(texts)}: {text[:50]}... : {e}")
                embeddings_list.append([])
        return embeddings_list

    def embed_query(self, text: str) -> List[float]:
        """Embeds a single query text."""
        if self.client is None:
            raise RuntimeError("TextEmbeddingModel client is not initialized.")
        input_obj=TextEmbeddingInput(text, task_type="RETRIEVAL_QUERY")
        embeddings=self.client.get_embeddings([input_obj])
        return list(embeddings[0].values)

