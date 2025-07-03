# check_vertex_ai.py
import os
from dotenv import load_dotenv
import vertexai
from vertexai.language_models import TextEmbeddingModel, TextEmbeddingInput
from vertexai.generative_models import GenerativeModel

load_dotenv()

try:
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION")

    if not project_id:
        raise ValueError("GOOGLE_CLOUD_PROJECT not set in .env file.")
    if not location:
        raise ValueError("GOOGLE_CLOUD_LOCATION not set in .env file.")

    vertexai.init(project=project_id, location=location)
    print(f"Vertex AI initialized for project: {project_id}, location: {location}")

    # Try to load a generative model (Gemini)
    try:
       # model = GenerativeModel("gemini-1.5-flash")
        print("Successfully loaded Gemini 1.5 Flash model.")
    except Exception as e:
        print(f"Failed to load Gemini 1.5 Flash model: {e}")
        print("Please ensure you have access to this model and GOOGLE_API_KEY (if used by LangChain) is correct.")

    # Try to generate an embedding
    try:
        embedding_model = TextEmbeddingModel.from_pretrained("gemini-embedding-001")
        test_text = "Hello, world!"
        response = embedding_model.get_embeddings([test_text])
        embedding_values = response[0].values
        print(f"Successfully generated embedding for '{test_text}'. Dimension: {len(embedding_values)}")
    except Exception as e:
        print(f"Failed to generate embedding: {e}")
        print("Please ensure 'gemini-embedding-001' is available in your region and project.")

except Exception as e:
    print(f"An error occurred during Vertex AI setup check: {e}")
    print("Please review your Google Cloud setup, .env variables, and gcloud authentication.")