"""
Configuration Module

This module provides configuration settings for the application.
It loads environment variables from a .env file and provides default values.

"""

import os
import json
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from typing import Dict, List, Optional, Any, Union

# Load environment variables from .env file
load_dotenv()

def parse_nitter_instances(env_value: str) -> List[str]:
    """Parse NITTER_INSTANCES from environment variable with fallback"""
    try:
        if not env_value:
            return ["https://nitter.net"]
        # Try to parse as JSON array
        instances = json.loads(env_value)
        if not isinstance(instances, list):
            raise ValueError("NITTER_INSTANCES must be a JSON array")
        return instances
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Warning: Invalid NITTER_INSTANCES format: {e}")
        return ["https://nitter.net"]

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
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o-mini"
    
    # SERP API
    SERPAPI_KEY: str
    
    # Twitter/Nitter
    TWITTER_NITTER_BASE_URL: str = os.getenv("TWITTER_NITTER_BASE_URL", "https://nitter.net")
    NITTER_INSTANCES: List[str] = parse_nitter_instances(os.getenv("NITTER_INSTANCES", ""))
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
    
    # Get project root directory
    PROJECT_ROOT: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
    
    # Set backend directory
    BACKEND_DIR: str = os.path.join(PROJECT_ROOT, "backend")
    
    # Set all data directories relative to backend
    DATA_DIR: str = os.path.join(BACKEND_DIR, "app", "data")
    RAW_DATA_DIR: str = os.path.join(DATA_DIR, "raw")
    JSON_INPUTS_DIR: str = os.path.join(DATA_DIR, "json_inputs")
    LOGS_DIR: str = os.path.join(DATA_DIR, "logs")
    PROCESSED_DATA_DIR: str = os.path.join(DATA_DIR, "processed")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create all data directories
        for dir_path in [self.DATA_DIR, self.RAW_DATA_DIR, self.JSON_INPUTS_DIR, 
                        self.LOGS_DIR, self.PROCESSED_DATA_DIR]:
            os.makedirs(dir_path, exist_ok=True)
    
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