##### config.py #####
"""
Centralized Configuration Management

Uses pydantic-settings for robust environment handling.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    ENV: str = "development"  # Set to "production" when deploying

    # Database Configuration (Must be set in .env)
    DB_URL: str  
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10

    # API Keys (Must be set in .env)
    SERPAPI_KEY: str  
    OPENAI_API_KEY: str  
    LINKEDIN_API_KEY: str  

    # Redis Configuration (Must be set in .env)
    REDIS_URL: str  

    # Security & Rate-Limiting
    CORS_ORIGINS: List[str] = ["*"]
    RATE_LIMIT: str = "100/minute"

    # Proxy Configuration (Optional)
    PROXY_LIST: List[str] = []

    model_config = SettingsConfigDict(
        env_file=".env",  # Load environment variables from .env
        env_file_encoding="utf-8"
    )

settings = Settings()
