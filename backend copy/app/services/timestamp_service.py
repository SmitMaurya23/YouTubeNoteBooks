

import sys
from langchain_google_vertexai import ChatVertexAI
from app.repositories.vector_repository import VectorRepository
from app.schemas.schema import TimestampEntry, TimestampResponse
from langchain.output_parsers import PydanticOutputParser
from typing import List, Dict
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

class TimestampService:
    """
    Handles all business logic related to extracting precise timestamps from a video transcript
    using a Retrieval-Augmented Generation (RAG) approach.
    """

    def __init__(self, llm: ChatVertexAI, vector_repository: VectorRepository):
        self.llm=llm
        self.vector_repository=vector_repository

    def _format_timestamp(self, seconds: float)->str:
        """Converts seconds into a human-readable HH:MM:SS or MM:SS format."""
        minutes,seconds=divmod(int(seconds),60)
        hours, minutes=divmod(minutes,60)
        if hours>0:
            return f"{hours:02}:{minutes:02}:{seconds:02}"
        return f"{minutes:02}:{seconds:02}"

    def _format_docs_for_timestamp_llm(self, docs:List[Document])->str:
        """Helper function to format retrieved documents into a simple, list-based string for the LLM."""
        if not docs:
            return "No relevant cotnext found."
        formatted_segments=[]
        for i, doc in enumerate(docs):
            if 'start' in doc.metadata:
                formatted_segments.append(
                    f"Timestamp: {self._format_timestamp(doc.metadata['start'])} | Text: \"{doc.page_content}\""
                )
        return "\n---\n".join(formatted_segments)

    async def get_timestamps_for_query(
            self, query_text: str, video_id:str, k: int=5
    )->List[TimestampEntry]:
        """
        Retrieves the most relevant timestamps for a given query using a RAG chain
        with structured Pydantic output parsing.
        """
        print(f"Searching for timestamps for query: '{query_text}' in  video: {video_id}")

        try:
            retriever_docs=self.vector_repository.similarity_search_query(query=query_text,k=k,filter={"video_id":video_id})
        except Exception as e:
            print(f"Error retrieving documents from vector store: {e}", file=sys.stderr)
            return []
        context=self._format_docs_for_timestamp_llm(retriever_docs)

        parser=PydanticOutputParser(pydantic_object=TimestampResponse)
        prompt=ChatPromptTemplate.from_messages(
            [
                ("system",
                 "You are an expert assistant at extracting precise timestamps from video transcripts. "
                 "Given the user's query and relevant transcript segments, "
                 "identify the most precise start times where the topic '{query}' is discussed. "
                 "Only provide timestamps from the provided segments.\n\n"
                 "Transcript Segments:\n{context}\n\n"
                 "Provide a list of up to 3 relevant timestamps and a very brief (1-2 sentences) snippet of "
                 "the text that directly relates to that timestamp. If the topic is not clearly present, "
                 "return an empty list. "
                 "Do not make up answers or timestamps. "
                 "Format your final output as a single JSON object that conforms to the following schema:\n{format_instructions}"
                ),
                ("user", "Query: {query}"),
            ]
        )

        timestamp_rag_chain=(
            {"context": lambda x: context, "query": RunnablePassthrough(), "format_instructions": lambda x: parser.get_format_instructions()
            }
            | prompt
            | self.llm
            | parser
        )

        try:
            response_obj=await timestamp_rag_chain.ainvoke(query_text)
            print(f"LLM successfully parsed into Pydantic object. ")
            return response_obj.results
        except Exception as e:
            print(f"Error in RAG chain or parsing LLM response: {e}", file=sys.stderr)
            raise




