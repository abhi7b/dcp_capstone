# config/config.py
"""
Configuration management for the DCP AI Scouting Platform.

This module provides a centralized configuration system that loads settings from
environment variables, .env files, and default values. It uses Pydantic for validation
and type checking.
"""
import os
import json
from typing import List, Dict, Any, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    """Main settings class for the DCP AI Scouting Platform."""
    
    # Core settings
    ENV: str = Field(default="development", description="Environment (development, staging, production)")
    DEBUG: bool = Field(default=False, description="Debug mode")
    API_PREFIX: str = Field(default="/api/v1", description="API prefix for all endpoints")
    PROJECT_NAME: str = Field(default="DCP AI Scouting Platform", description="Project name")
    
    # Database settings
    DATABASE_URL: str = Field(default="postgresql+asyncpg://postgres:dukecapital!@db.aioxaiupracfehvkjogu.supabase.co:5432/postgres", description="Database connection URL")
    DATABASE_POOL_SIZE: int = Field(default=20, description="Database connection pool size")
    DATABASE_MAX_OVERFLOW: int = Field(default=10, description="Maximum number of connections to overflow")
    
    # OpenAI settings
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API key")
    OPENAI_MODEL: str = Field(default="gpt-4o-mini", description="OpenAI model to use")
    OPENAI_MAX_TOKENS: int = Field(default=4000, description="Maximum tokens for OpenAI requests")
    OPENAI_TEMPERATURE: float = Field(default=0.0, description="Temperature for OpenAI requests")
    
    # Scraper settings
    SERPAPI_KEY: str = Field(default="", description="SerpAPI key")
    SCRAPER_MAX_CONCURRENT: int = Field(default=5, description="Maximum concurrent scraper requests")
    SCRAPER_TIMEOUT: int = Field(default=30, description="Scraper timeout in seconds")
    SCRAPER_MAX_RETRIES: int = Field(default=3, description="Maximum scraper retries")
    SCRAPER_PROXY_LIST: List[str] = Field(default=[], description="List of proxies for scraping")
    SCRAPER_DAILY_QUOTA: int = Field(default=100, description="Daily quota for scraper requests")
    
    # Twitter settings
    TWITTER_API_KEY: str = Field(default="", description="Twitter API key")
    TWITTER_API_SECRET: str = Field(default="", description="Twitter API secret")
    TWITTER_ACCESS_TOKEN: str = Field(default="", description="Twitter access token")
    TWITTER_ACCESS_SECRET: str = Field(default="", description="Twitter access secret")
    TWITTER_NITTER_BASE_URL: str = Field(default="https://nitter.net", description="Nitter base URL")
    TWITTER_MAX_TWEETS: int = Field(default=100, description="Maximum tweets to fetch")
    
    # Security settings
    SECURITY_JWT_SECRET: str = Field(default="", description="JWT secret key")
    SECURITY_JWT_ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    SECURITY_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, description="Access token expiration in minutes")
    
    # Cache settings
    REDIS_URL: str = Field(default="redis://localhost:6379/0", description="Redis URL for caching")
    CACHE_DEFAULT_TTL: int = Field(default=3600, description="Default cache TTL in seconds")
    CACHE_COMPANY_TTL: int = Field(default=86400, description="Company cache TTL in seconds")
    CACHE_FOUNDER_TTL: int = Field(default=86400, description="Founder cache TTL in seconds")
    CACHE_SEARCH_TTL: int = Field(default=3600, description="Search cache TTL in seconds")
    
    # Logging settings
    LOG_LEVEL: str = Field(default="INFO", description="Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)")
    LOG_FORMAT: str = Field(default="console", description="Log format (console, json)")
    LOG_FILE_ENABLED: bool = Field(default=True, description="Enable file logging")
    LOG_FILE_PATH: str = Field(default="logs", description="Log file path")
    
    # CORS settings
    CORS_ORIGINS: List[str] = Field(default=["http://localhost:3000"], description="CORS origins")
    
    @field_validator("SCRAPER_PROXY_LIST", mode="before")
    def parse_proxy_list(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v) if v.startswith("[") else [x.strip() for x in v.split(",") if x.strip()]
            except json.JSONDecodeError:
                return []
        return v
    
    @field_validator("CORS_ORIGINS", mode="before")
    def parse_origins(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [x.strip() for x in v.split(",") if x.strip()]
        return v
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    
    # For backward compatibility with nested settings
    @property
    def database(self):
        """Backward compatibility for database settings."""
        return type('DatabaseSettings', (), {
            'URL': self.DATABASE_URL,
            'POOL_SIZE': self.DATABASE_POOL_SIZE,
            'MAX_OVERFLOW': self.DATABASE_MAX_OVERFLOW
        })
    
    @property
    def openai(self):
        """Backward compatibility for OpenAI settings."""
        return type('OpenAISettings', (), {
            'API_KEY': self.OPENAI_API_KEY,
            'MODEL': self.OPENAI_MODEL,
            'MAX_TOKENS': self.OPENAI_MAX_TOKENS,
            'TEMPERATURE': self.OPENAI_TEMPERATURE
        })
    
    @property
    def scraper(self):
        """Backward compatibility for scraper settings."""
        return type('ScraperSettings', (), {
            'SERPAPI_KEY': self.SERPAPI_KEY,
            'MAX_CONCURRENT': self.SCRAPER_MAX_CONCURRENT,
            'TIMEOUT': self.SCRAPER_TIMEOUT,
            'MAX_RETRIES': self.SCRAPER_MAX_RETRIES,
            'PROXY_LIST': self.SCRAPER_PROXY_LIST,
            'DAILY_QUOTA': self.SCRAPER_DAILY_QUOTA
        })
    
    @property
    def twitter(self):
        """Backward compatibility for Twitter settings."""
        return type('TwitterSettings', (), {
            'API_KEY': self.TWITTER_API_KEY,
            'API_SECRET': self.TWITTER_API_SECRET,
            'ACCESS_TOKEN': self.TWITTER_ACCESS_TOKEN,
            'ACCESS_SECRET': self.TWITTER_ACCESS_SECRET,
            'NITTER_BASE_URL': self.TWITTER_NITTER_BASE_URL,
            'MAX_TWEETS': self.TWITTER_MAX_TWEETS
        })
    
    @property
    def security(self):
        """Backward compatibility for security settings."""
        return type('SecuritySettings', (), {
            'JWT_SECRET': self.SECURITY_JWT_SECRET,
            'JWT_ALGORITHM': self.SECURITY_JWT_ALGORITHM,
            'ACCESS_TOKEN_EXPIRE_MINUTES': self.SECURITY_ACCESS_TOKEN_EXPIRE_MINUTES
        })
    
    @property
    def cache(self):
        """Backward compatibility for cache settings."""
        return type('CacheSettings', (), {
            'REDIS_URL': self.REDIS_URL,
            'DEFAULT_TTL': self.CACHE_DEFAULT_TTL,
            'COMPANY_TTL': self.CACHE_COMPANY_TTL,
            'FOUNDER_TTL': self.CACHE_FOUNDER_TTL,
            'SEARCH_TTL': self.CACHE_SEARCH_TTL
        })
    
    @property
    def logging(self):
        """Backward compatibility for logging settings."""
        return type('LoggingSettings', (), {
            'LEVEL': self.LOG_LEVEL,
            'FORMAT': self.LOG_FORMAT,
            'FILE_ENABLED': self.LOG_FILE_ENABLED,
            'FILE_PATH': self.LOG_FILE_PATH
        })
    
    @property
    def cors(self):
        """Backward compatibility for CORS settings."""
        return type('CORSSettings', (), {
            'ORIGINS': self.CORS_ORIGINS
        })

# Create a global settings instance
settings = Settings()

# Helper functions (kept for backward compatibility)
def get_settings() -> Settings:
    """Get the settings instance."""
    return settings

def get_db_url() -> str:
    """Get the database URL."""
    return settings.DATABASE_URL

def get_serpapi_key() -> str:
    """Get the SerpAPI key."""
    return settings.SERPAPI_KEY

def get_openai_api_key() -> str:
    """Get the OpenAI API key."""
    return settings.OPENAI_API_KEY

def get_log_level() -> str:
    """Get the log level."""
    return settings.LOG_LEVEL
