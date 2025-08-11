from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    """
    Application settings class.
    Reads from environment variables and a .env file.
    """

    PORT: int = 8000
    HOST: str = "localhost"
    MONGODB_URI: Optional[str] = None
    MongoPassword: Optional[str] = None
    DB_NAME: Optional[str] = None
    COLLECTION_NAME: Optional[str] = None
    INDEX_NAME: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    GOOGLE_CLOUD_PROJECT: Optional[str] = None
    GOOGLE_CLOUD_LOCATION: Optional[str] = None
    GOOGLE_APPLICATION_CREDENTIALS_JSON: Optional[str] = None
    GEMINI_DESCRIPTION_MODEL: Optional[str] = None
    GEMINI_TEMPERATURE: Optional[str] = None
    EMBEDDINGS_MODEL_NAME: Optional[str] = None
    TIMESTAMP_LLM_MODEL: Optional[str] = None
    TIMESTAMP_TEMPERATURE: Optional[str] = None


    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
