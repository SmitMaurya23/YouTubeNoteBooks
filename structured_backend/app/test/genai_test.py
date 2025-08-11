# test_genai.py
import os
import sys
import json
from dotenv import load_dotenv
import asyncio

# Add the parent directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

load_dotenv()
import traceback

from app.core.settings import settings
from app.core.dependencies import get_gemini_model
from app.services.genai_service import GenAIService
from app.schemas.schema import VideoDescription

def save_description_as_json(description: VideoDescription, filename: str = "video_description.json"):
    """
    Saves a Pydantic VideoDescription object to a JSON file.
    """
    results_dir = "results"
    # Create the results directory if it doesn't exist
    os.makedirs(results_dir, exist_ok=True)

    file_path = os.path.join(results_dir, filename)

    try:
        # Convert the Pydantic object to a dictionary
        data_to_save = description.model_dump()
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, indent=4)
        print(f"Successfully saved description to {file_path}")
    except Exception as e:
        print(f"Error saving JSON file: {e}")
        raise

async def run_test():
    print("\n--- Starting GenAI Service Functionality Test ---")

    # --- 1. Manual Dependency Initialization ---
    print("\nInitializing GenAI service...")
    try:
        llm_model = get_gemini_model()
        genai_service = GenAIService(llm=llm_model)
    except Exception as e:
        print(f"Error during service initialization: {e}")
        return

    # --- 2. Define Sample Data ---
    sample_transcript = """
    Is ChatGPT Helping or Hurting Your Developers’ Productivity?

Is ChatGPT Helping or Hurting Your Developers’ Productivity?
By: Ariel Assaraf on July 13, 2023

ChatGPT’s ability to translate natural language into working code has sparked tremendous interest in the programming community. Developers are exploring ways to use ChatGPT to reduce redundant tasks, from creating code snippets to analyzing and debugging programs. This also allows them to focus on more complex tasks like data analysis and monitoring with the help of a strong full-stack observability platform. Despite ChatGPT’s impressive capabilities, developers and their employers are split on whether the AI chatbot significantly boosts developer productivity.

We will explore how to use ChatGPT to benefit your developers’ productivity and go over the advantages and disadvantages of ChatGPT to help you make the right decision for your business.

How to use ChatGPT for Better Productivity
ChatGPT has quickly become the most popular intelligence chatbot, with over a million user signups in its first five days and over 100 million in the first two months. Here are a few ways ChatGPT, developed by OpenAI, can help boost productivity in your organization.

Improve Their Code
Sometimes manually written code snippets consume additional CPU resources. Using ChatGPT, developers can optimize their functions for better performance. Additionally, ChatGPT can also write test cases and spot security vulnerabilities in their code, helping developers work faster.

Simplify Documentation
ChatGPT can give a simple explanation for the layman, avoiding technical jargon to a large extent. For instance, a developer at Twitter fed ChatGPT their code and it responded with a pretty detailed explanation. Using ChatGPT to generate the first draft of a company’s internal documentation would make knowledge transfers easier. New hires could quickly get up to speed on the company’s codebase. Further, ChatGPT could also be used for external-facing documents where other developers can learn how to use the company’s APIs and frameworks.

Test and Understand Code
ChatGPT can write automated tests for code that is fed into it. Although many developers consider testing boring and stressful—and sometimes a waste of time—it’s a critical step in ensuring that published applications are bug-free.
    """
    print("Using a sample transcript for testing.")

    # --- 3. Run the Core Logic ---
    try:
        print("\nGenerating video description with Gemini...")
        description = await genai_service.generate_video_description(sample_transcript)

        # --- 4. Verify the Output ---
        print("\n--- Generation Successful ---")
        print("Generated Title:", description.title)
        print("Generated Summary:", description.summary)
        print("Generated Keywords:", description.keywords)
        print("Generated Category Tags:", description.category_tags)
        print("Generated Detailed Description:", description.detailed_description)
        # --- 5. Store the output as a JSON file ---
        save_description_as_json(description)

        print("\nVerification successful. The output matches the expected Pydantic schema.")

    except Exception as e:
        print(f"\nAn error occurred during the description generation process: {e}")
        traceback.print_exc()
        return

    print("\n--- Test Finished ---")

if __name__ == "__main__":
    asyncio.run(run_test())