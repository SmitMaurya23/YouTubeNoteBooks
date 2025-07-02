from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
import re
import json

# Load environment variables from .env file
load_dotenv()

# --- Initialize Gemini Model ---
# Use "gemini-1.5-pro" or "gemini-1.5-flash"
# These are the current stable and generally available models for text generation.
try:
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.7)
    # temperature controls creativity (0.0-1.0), adjust as needed
except Exception as e:
    print(f"Error initializing Gemini model: {e}")
    print("Please ensure GOOGLE_API_KEY is set correctly in your .env file and the model name is valid.")
    llm = None


def generate_description(transcript_text: str) -> dict:
    """Generate a structured video description from transcript using a free Gemini model."""

    if llm is None:
        print("Gemini model not initialized. Cannot generate description.")
        return {
            "title": "Error: Model Not Initialized",
            "keywords": [],
            "category_tags": [], # Added for consistency in error state
            "detailed_description": "Error",
            "summary": "Error"
        }

    # Define prompt for structured output
    # We'll emphasize JSON output for better parsing with Gemini
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

    # Generate description
    chain = prompt_template | llm

    # Invoke the chain and get the raw output
    try:
        result = chain.invoke({"transcript": transcript_text})
        # Handle different possible return types
        if isinstance(result, dict) and "content" in result:
            raw_output = str(result["content"]).strip()
        elif hasattr(result, "content"):
            raw_output = str(result.content).strip()
        elif isinstance(result, str):
            raw_output = result.strip()
        elif isinstance(result, list) and result:
            # If it's a list, join string elements or extract 'content' from dicts
            if all(isinstance(item, str) for item in result):
                raw_output = " ".join(result).strip()
            elif all(isinstance(item, dict) and "content" in item for item in result):
                raw_output = " ".join(str(item.get("content", "")) for item in result if isinstance(item, dict) and "content" in item).strip()
            else:
                raw_output = str(result).strip()
        else:
            raw_output = str(result).strip()
    except Exception as e:
        print(f"Error during Gemini API call: {e}")
        # Fallback in case of API error
        return {
            "title": "API Error",
            "keywords": [],
            "category_tags": [], # Added for consistency in error state
            "detailed_description": "API Error",
            "summary": "API Error"
        }

    # Parse the JSON output
    try:
        # Use a more robust JSON parsing approach,
        # sometimes LLMs can add conversational text outside JSON.
        # This regex tries to find the first JSON object.
        json_match = re.search(r'```json\n({.*?})\n```', raw_output, re.DOTALL)
        if not json_match:
            json_match = re.search(r'({.*?})', raw_output, re.DOTALL)

        if json_match:
            json_string = json_match.group(1)
            parsed_data = json.loads(json_string)

            # Ensure the keys match your expected structure
            title = parsed_data.get("title", "N/A")
            keywords = parsed_data.get("keywords", []) # Join list to string
            category_tags = parsed_data.get("category_tags", []) # Extract as a list

            # Format detailed description to match your old output (separated by ||)
            detailed_description_list = parsed_data.get("detailed_description", [])
            detailed_description = "||".join(detailed_description_list)

            summary = parsed_data.get("summary", "N/A").replace('\n', '||')

            return {
                "title": title,
                "keywords": keywords,
                "category_tags": category_tags, # Include the new field
                "detailed_description": detailed_description,
                "summary": summary
            }
        else:
            raise ValueError("No valid JSON found in LLM output.")

    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}\nRaw output: {raw_output}")
        # Fallback: Return a default structured response if parsing fails
        return {
            "title": "Parsing Error",
            "keywords": "Parsing Error",
            "category_tags": [], # Added for consistency in error state
            "detailed_description": "Parsing Error",
            "summary": "Parsing Error"
        }
    except Exception as e:
        print(f"An unexpected error occurred during parsing: {e}\nRaw output: {raw_output}")
        return {
            "title": "Unknown Error",
            "keywords": "Unknown Error",
            "category_tags": [], # Added for consistency in error state
            "detailed_description": "Unknown Error",
            "summary": "Unknown Error"
        }

