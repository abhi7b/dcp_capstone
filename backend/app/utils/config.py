import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from typing import Dict, List, Optional, Any, Union

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables with defaults.
    Settings are validated using Pydantic's BaseSettings.
    """
    # Core settings
    PROJECT_NAME: str = "Duke VC Insight Engine"
    VERSION: str = "1.0.0"
    
    # API Settings
    API_SECRET_KEY: str = os.getenv("API_SECRET_KEY", "supersecretkey")
    API_ALGORITHM: str = os.getenv("API_ALGORITHM", "HS256")
    API_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("API_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    DATABASE_USER: str = os.getenv("DATABASE_USER", "postgres")
    DATABASE_PASSWORD: str = os.getenv("DATABASE_PASSWORD", "")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "postgres")
    
    # OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    # SERP API
    SERPAPI_KEY: str = os.getenv("SERPAPI_KEY", "")
    
    # Twitter/Nitter
    TWITTER_NITTER_BASE_URL: str = os.getenv("TWITTER_NITTER_BASE_URL", "https://nitter.net")
    TWITTER_API_KEY: str = os.getenv("TWITTER_API_KEY", "")
    TWITTER_API_SECRET: str = os.getenv("TWITTER_API_SECRET", "")
    TWITTER_ACCESS_TOKEN: str = os.getenv("TWITTER_ACCESS_TOKEN", "")
    TWITTER_ACCESS_SECRET: str = os.getenv("TWITTER_ACCESS_SECRET", "")
    
    # Redis and Celery
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", REDIS_URL)
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)
    
    # Scoring thresholds 
    MINIMUM_DUKE_AFFILIATION_SCORE: float = float(os.getenv("MINIMUM_DUKE_AFFILIATION_SCORE", "0.7"))
    MINIMUM_RELEVANCE_SCORE: float = float(os.getenv("MINIMUM_RELEVANCE_SCORE", "0.6"))
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Get user home directory - used as fallback
    HOME_DIR: str = os.path.expanduser("~")
    
    # File paths - avoid using /app paths
    BASE_DIR: str = os.getenv("BASE_DIR", os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
    if BASE_DIR.startswith("/app"):
        BASE_DIR = os.path.join(HOME_DIR, "duke_vc_insight_engine")
    
    # Set backend directory as fixed location for data
    BACKEND_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
    
    # Set all data directories as subdirectories of BACKEND_DIR/data
    DATA_DIR: str = os.getenv("DATA_DIR", os.path.join(BACKEND_DIR, "data"))
    RAW_DATA_DIR: str = os.getenv("RAW_DATA_DIR", os.path.join(DATA_DIR, "raw"))
    JSON_INPUTS_DIR: str = os.getenv("JSON_INPUTS_DIR", os.path.join(DATA_DIR, "json_inputs"))
    LOGS_DIR: str = os.getenv("LOGS_DIR", os.path.join(DATA_DIR, "logs"))
    
    class Config:
        """Pydantic settings configuration"""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # Allow extra fields from .env file

        @classmethod
        def customise_sources(cls, init_settings, env_settings, file_secret_settings):
            """Customize settings loading priority:
            1. Environment variables
            2. .env file
            3. Default values in the model
            """
            return env_settings, file_secret_settings, init_settings

# Create settings instance
settings = Settings()

# Export settings as dictionary for easier access in other modules
settings_dict: Dict[str, Any] = {
    k: v for k, v in settings.dict().items() 
    if not k.startswith("_") and not callable(v)
} 