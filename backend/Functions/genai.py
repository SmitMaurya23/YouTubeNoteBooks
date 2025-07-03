# genai.py
import os
from dotenv import load_dotenv
import re
import json

# Import the correct LangChain integration for Vertex AI generative models
from langchain_google_vertexai import ChatVertexAI
from langchain.prompts import PromptTemplate

load_dotenv()

# --- Environment Variables for Vertex AI ---
# These should be consistent across all modules
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

if not GOOGLE_CLOUD_PROJECT:
    raise ValueError("GOOGLE_CLOUD_PROJECT not set in .env file for genai.")
# GOOGLE_CLOUD_LOCATION is optional, defaults to us-central1

# --- Initialize Gemini Model for Description Generation ---
gemini_description_model = None
try:
    gemini_description_model = ChatVertexAI(
        model_name="gemini-2.0-flash", # Changed model name to align with working model in chatBot.py
        temperature=0.7, # Higher temperature for more creative/descriptive output
        project=GOOGLE_CLOUD_PROJECT,
        location=GOOGLE_CLOUD_LOCATION,
    )
    print("Description generation LLM (Gemini 2.0 Flash) initialized in genai.py.")
except Exception as e:
    print(f"Error initializing description generation LLM in genai.py: {e}")
    print("Please ensure Vertex AI API is enabled for Gemini 2.0 Flash in your project and location.")
    gemini_description_model = None


def generate_description_with_gemini(transcript_text: str) -> dict:
    """
    Generates a structured video description from transcript using a Gemini model
    via Vertex AI.

    Args:
        transcript_text (str): The plain text transcript of the video.

    Returns:
        dict: A dictionary containing the structured video description (title, keywords, etc.).
    """
    if gemini_description_model is None:
        print("Gemini description model not initialized. Cannot generate description.")
        return {
            "title": "Error: Model Not Initialized",
            "keywords": [],
            "category_tags": [],
            "detailed_description": "Error",
            "summary": "Error"
        }

    # Define prompt for structured JSON output
    prompt_template = PromptTemplate(
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

    # Create a LangChain chain with the prompt and the LLM
    chain = prompt_template | gemini_description_model

    # Invoke the chain and get the raw output from the LLM
    try:
        result = chain.invoke({"transcript": transcript_text})
        # Extract content from the result object, which is typically a LangChain AIMessage
        raw_output = str(result.content).strip()
    except Exception as e:
        print(f"Error during Gemini API call for description generation: {e}")
        # Fallback in case of API error
        return {
            "title": "API Error",
            "keywords": [],
            "category_tags": [],
            "detailed_description": "API Error",
            "summary": "API Error"
        }

    # Parse the JSON output from the raw string
    try:
        # Use regex to robustly find the JSON block, even if wrapped in markdown
        json_match = re.search(r'```json\n({.*?})\n```', raw_output, re.DOTALL)
        if not json_match:
            # Fallback for cases where LLM doesn't wrap in ```json
            json_match = re.search(r'({.*?})', raw_output, re.DOTALL)

        if json_match:
            json_string = json_match.group(1)
            parsed_data = json.loads(json_string)

            # Extract and format data, providing defaults to prevent KeyError
            title = parsed_data.get("title", "N/A")
            keywords = parsed_data.get("keywords", [])
            category_tags = parsed_data.get("category_tags", [])

            # Join detailed_description list into a single string with '||' delimiter
            detailed_description_list = parsed_data.get("detailed_description", [])
            detailed_description = "||".join(detailed_description_list)

            # Replace newlines in summary with '||' for consistency if needed
            summary = parsed_data.get("summary", "N/A").replace('\n', '||')

            return {
                "title": title,
                "keywords": keywords,
                "category_tags": category_tags,
                "detailed_description": detailed_description,
                "summary": summary
            }
        else:
            raise ValueError("No valid JSON found in LLM output.")

    except json.JSONDecodeError as e:
        print(f"JSON parsing error in genai.py: {e}\nRaw output: {raw_output}")
        # Fallback: Return a default structured response if parsing fails
        return {
            "title": "Parsing Error",
            "keywords": [],
            "category_tags": [],
            "detailed_description": "Parsing Error",
            "summary": "Parsing Error"
        }
    except Exception as e:
        print(f"An unexpected error occurred during parsing in genai.py: {e}\nRaw output: {raw_output}")
        return {
            "title": "Unknown Error",
            "keywords": [],
            "category_tags": [],
            "detailed_description": "Unknown Error",
            "summary": "Unknown Error"
        }
