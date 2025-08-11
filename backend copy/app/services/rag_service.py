# app/services/rag_service.py
from typing import List, Optional
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_google_vertexai import ChatVertexAI
from langchain_mongodb import MongoDBAtlasVectorSearch

class BasicRAGService:
    """
    Component 1: A core RAG service that answers a query using a vector store,
    without any conversation history.
    """
    def __init__(self, llm: ChatVertexAI, vector_store: MongoDBAtlasVectorSearch):
        self.llm = llm
        self.vector_store = vector_store

        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system",
                 "You are a helpful assistant for YouTube video content. "
                 "Use the following retrieved video transcript excerpts to answer the user's question. "
                 "If you don't know the answer based on the provided context, "
                 "politely state that you cannot find the answer in the given information. "
                 "You can make up answers but explicitly mention that this is outside of video information. Be concise but informative."
                ),
                ("user", "Context: {context}\nQuestion: {question}"),
            ]
        )
        self.rag_chain = (
            RunnablePassthrough.assign(
                # Use .get() to safely handle missing 'video_id' key
                context=lambda x: self._get_retriever_chain(
                    x["question"], x.get("video_id")
                ),
            )
            | self.prompt
            | self.llm
            | StrOutputParser()
        )

    def _format_docs(self, docs: List[Document]) -> str:
        if not docs:
            return "No relevant video context found."
        return "\n\n".join(doc.page_content for doc in docs)

    def _get_retriever_chain(self, question: str, video_id: Optional[str]):
        # Initialize a base dictionary with the required 'k' parameter.
        search_kwargs = {"k": 5, "pre_filter":None}

        # Conditionally add the 'pre_filter' key only if video_id is provided.
        if video_id:
            search_kwargs["pre_filter"] = {"video_id": video_id}

        # The search_kwargs dictionary now has a clear and correct structure
        # for the type checker.
        retriever = self.vector_store.as_retriever(search_kwargs=search_kwargs)

        return self._format_docs(retriever.invoke(question))

    async def get_response(self, query_text: str, video_id: Optional[str] = None) -> str:
        """Generates a response to a single query using RAG."""
        try:
            # Pass video_id in the input dictionary
            response = await self.rag_chain.ainvoke({"question": query_text, "video_id": video_id})
            return response
        except Exception as e:
            print(f"Error in BasicRAGService: {e}")
            return f"Error generating response: {e}"