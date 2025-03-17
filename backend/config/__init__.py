"""
Configuration package for the DCP AI Scouting Platform.

This package provides centralized configuration management for the application,
including settings, logging, and caching.

Key Components:
- Settings: Pydantic-based configuration with environment variable support
- Logging: Structured logging with console and file output
- Caching: Redis-based caching with key generation and invalidation

Usage:
    from backend.config import settings, get_logger, init_logging, init_cache
    
    # Initialize logging
    init_logging()
    
    # Get a logger
    logger = get_logger(__name__)
    
    # Access settings
    db_url = settings.DATABASE_URL
    
    # Initialize cache (in an async context)
    await init_cache()
    
    # Use the cache decorator
    from backend.config import cached
    
    @cached("company")
    async def get_company(name: str):
        # This function's results will be cached
        ...
"""

# Import settings and helper functions
from backend.config.config import (
    settings,
    get_settings,
    get_db_url,
    get_serpapi_key,
    get_openai_api_key,
    get_log_level
)

# Import logging components
from backend.config.logs import (
    LogManager,
    get_logger,
    init_logging
)

# Import cache components
from backend.config.cache import (
    CacheManager,
    cached,
    invalidate_company_cache,
    invalidate_founder_cache,
    invalidate_search_cache,
    invalidate_twitter_cache,
    invalidate_duke_alumni_cache
)

# Convenience functions for cache management
async def init_cache():
    """Initialize the cache system."""
    await CacheManager.init_cache()

async def close_cache():
    """Close the cache system."""
    await CacheManager.close()

# Export commonly used functions and classes
__all__ = [
    # Config
    "settings",
    "get_settings",
    "get_db_url",
    "get_serpapi_key",
    "get_openai_api_key",
    "get_log_level",
    
    # Logging
    "LogManager",
    "get_logger",
    "init_logging",
    
    # Caching
    "CacheManager",
    "cached",
    "init_cache",
    "close_cache",
    "invalidate_company_cache",
    "invalidate_founder_cache",
    "invalidate_search_cache",
    "invalidate_twitter_cache",
    "invalidate_duke_alumni_cache"
] 