import re
import json
from langchain_google_vertexai import ChatVertexAI
from langchain.prompts import PromptTemplate
from app.core.schema import VideoDescription
from typing import  Dict, Any

class GenAIService:
    def __init__(self,llm:ChatVertexAI):

        self.llm=llm

        self.prompt_template=PromptTemplate(
        input_variables=["transcript"],
        template="""
        As an expert video content analyst, your task is to generate a structured description of a YouTube video based on the provided transcript. The output MUST be in a strict JSON format.

        Here's the required JSON schema:
        {{
          "title": "A concise and descriptive title for the video",
          "keywords": ["keyword1", "keyword2", "keyword3", "...", "keywordN"],
          "category_tags": ["tag1", "tag2", "tag3", "...", "tagN"],
          "detailed_description": [
            "Point 1: Detailed explanation of the point.",
            "Point 2: Another detailed explanation.",
            "Point 3: And so on."
          ],
          "summary": "A concise summary of the video in 1-2 paragraphs. Keep it engaging and informative."
        }}

        Ensure that:
        - The "title" is a single string.
        - The "keywords" is an array of strings.
        - The "category_tags" is an array of strings, categorizing the video content (e.g., "Technology", "Education", "Vlog", "Gaming", "Tutorial").
        - The "detailed_description" is an array of strings, where each string is a distinct point starting with "Point X: ".
        - The "summary" is a single string that can contain multiple sentences forming 1-2 paragraphs.

        Transcript:
        {transcript}
        """
        )

        self.chain = self.prompt_template | self.llm

    async def generate_video_description(self,transcript_text:str) -> VideoDescription:

        """
        Generates a structured video description from a transcript using the LLM.
        """

        try:
            result=self.chain.invoke({"transcript":transcript_text})
            raw_output=str(result.content).strip()
            parsed_data=self._parse_json_from_llm_output(raw_output)

            return VideoDescription(**parsed_data)

        except Exception as e:
            print(f"Error during video description generation: {e}")
            raise RuntimeError(f"Failed to generate description: {e}") from e


    #NOT USING THE BELOW FUCNTION FOR NOW
    def _parse_json_from_llm_output(self, raw_output: str) -> Dict[str, Any]:
        """
        Internal method to parse the JSON block from the LLM's raw output.
        """

        try:
            json_match = re.search(r'```json\n({.*?})\n```', raw_output, re.DOTALL)
            if not json_match:
                json_match = re.search(r'({.*?})', raw_output, re.DOTALL)

            if json_match:
                json_string = json_match.group(1)
                parsed_data = json.loads(json_string)
                # We can now return the raw dict, as Pydantic will handle validation
                return parsed_data
            else:
                raise ValueError("No valid JSON found in LLM output.")
        except (json.JSONDecodeError, ValueError) as e:
            print(f"JSON parsing error: {e}\nRaw output: {raw_output}")
            raise