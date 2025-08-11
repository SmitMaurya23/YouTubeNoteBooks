import json
import re
from typing import Dict, Any

from langchain_google_vertexai import ChatVertexAI
from langchain.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import PydanticOutputParser
from app.schemas.schema import VideoDescription

class GenAIService:
    def __init__(self, llm: ChatVertexAI):
        self.llm=llm
        self.parser=PydanticOutputParser(pydantic_object=VideoDescription)
        self.prompt_template=ChatPromptTemplate.from_messages(
            [
                ("system",
                 "As an expert video content analyst, your task is to generate a structured description of a YouTube video based on the provided transcript. The output MUST be a strict JSON object.\n"
                 "Generate a concise and descriptive title, relevant keywords, appropriate category tags, a detailed description broken down into key points, and a brief summary. "
                 "The output must conform to the following format instructions:\n{format_instructions}\n"
                 "Your response should ONLY contain the JSON object and nothing else."),
                 ("user","Transcript:\n{transcript}")
            ]
        )

        self.chain=(
            {"transcript": RunnablePassthrough(),
             "format_instructions": lambda x: self.parser.get_format_instructions()}
             | self.prompt_template
             | self.llm
             | self.parser
        )

    async def generate_video_description(self, transcript_text: str)-> VideoDescription:
        """
        Generates a structured video description from a transcript using the LLM.
        The chain now handles both the generation and the parsing of the output.
        """
        try:
            result: VideoDescription=await self.chain.ainvoke({"transcript": transcript_text})
            return result
        except Exception as e:
            print(f"Error during video description generation: {e}")
            raise RuntimeError(f"Failed to generate description: {e}") from e
