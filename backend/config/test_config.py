#!/usr/bin/env python3
"""
Tests for the configuration module.

This module contains tests for the configuration system, including settings,
logging, and caching.
"""
import asyncio
import logging
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add parent directory to path if running as script
if __name__ == "__main__" and __package__ is None:
    parent_dir = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(parent_dir))
    __package__ = "config"

# Import the modules to test
from backend.config import (
    settings,
    get_settings,
    get_db_url,
    get_serpapi_key,
    get_openai_api_key,
    get_log_level,
    get_logger,
    init_logging,
    init_cache,
    close_cache
)

# Initialize logger
logger = get_logger(__name__)

class TestConfig:
    """Test the configuration system."""
    
    def test_settings_access(self):
        """Test basic settings access."""
        # Test direct access to flattened settings
        assert settings.ENV in ["development", "staging", "production"]
        assert isinstance(settings.DEBUG, bool)
        assert settings.DATABASE_URL is not None
        assert settings.OPENAI_MODEL is not None
        
        # Test backward compatibility with nested settings
        assert settings.database.URL == settings.DATABASE_URL
        assert settings.openai.MODEL == settings.OPENAI_MODEL
        assert settings.scraper.SERPAPI_KEY == settings.SERPAPI_KEY
        assert settings.logging.LEVEL == settings.LOG_LEVEL
        assert settings.cache.REDIS_URL == settings.REDIS_URL
        
        # Test helper functions
        assert get_settings() is settings
        assert get_db_url() == settings.DATABASE_URL
        assert get_serpapi_key() == settings.SERPAPI_KEY
        assert get_openai_api_key() == settings.OPENAI_API_KEY
        assert get_log_level() == settings.LOG_LEVEL
        
        logger.info("✅ Settings tests passed")
        return True

class TestLogging:
    """Test the logging system."""
    
    def test_logging_setup(self):
        """Test logging setup and functionality."""
        # Initialize logging
        root_logger = init_logging()
        assert root_logger is not None
        
        # Get a logger
        test_logger = get_logger("test_logger")
        assert test_logger is not None
        
        # Test log levels
        test_logger.debug("Debug message")
        test_logger.info("Info message")
        test_logger.warning("Warning message")
        test_logger.error("Error message")
        test_logger.critical("Critical message")
        
        # Check log directory if file logging is enabled
        if settings.LOG_FILE_ENABLED:
            log_dir = Path(settings.LOG_FILE_PATH)
            assert log_dir.exists()
        
        logger.info("✅ Logging tests passed")
        return True

class TestCache:
    """Test the cache system."""
    
    async def test_cache_initialization(self):
        """Test cache initialization."""
        # Initialize cache
        await init_cache()
        from backend.config.cache import CacheManager
        
        # If Redis URL is empty, cache should not be initialized
        if not settings.REDIS_URL:
            assert not CacheManager.is_initialized()
            logger.info("✅ Cache initialization test passed (Redis URL not provided)")
            return True
        
        # Otherwise, cache should be initialized
        assert CacheManager.is_initialized()
        
        # Test cache key generation
        from backend.config.cache import CacheManager
        key = CacheManager.generate_key("company", name="test_company")
        assert key == "company:test_company"
        
        # Test cache decorator
        from backend.config import cached
        
        @cached("test")
        async def test_function(param: str):
            return {"param": param, "result": "test_result"}
        
        # Call the function to test caching
        result1 = await test_function("test_param")
        assert result1["param"] == "test_param"
        
        # Call again to test cache hit
        result2 = await test_function("test_param")
        assert result2["param"] == "test_param"
        assert result2 == result1
        
        # Test cache invalidation
        from backend.config.cache import CacheManager
        await CacheManager.delete_keys("test")
        
        # Close cache
        await close_cache()
        assert not CacheManager.is_initialized()
        
        logger.info("✅ Cache tests passed")
        return True

async def run_tests():
    """Run all tests."""
    success = True
    
    # Initialize logging
    init_logging()
    logger.info("Starting configuration tests")
    
    # Test settings
    config_tester = TestConfig()
    if not config_tester.test_settings_access():
        success = False
    
    # Test logging
    logging_tester = TestLogging()
    if not logging_tester.test_logging_setup():
        success = False
    
    # Test cache
    cache_tester = TestCache()
    if not await cache_tester.test_cache_initialization():
        success = False
    
    # Print summary
    if success:
        logger.info("All configuration tests passed!")
    else:
        logger.error("Some configuration tests failed!")
    
    return success

if __name__ == "__main__":
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1) 