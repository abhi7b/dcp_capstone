"""
Unit tests for the config module.
"""
import os
import pytest
from app.utils.config import Settings

def test_settings_loads_values():
    """Test that Settings loads values from environment variables."""
    # Setup test environment variables
    os.environ["API_SECRET_KEY"] = "test_secret_key"
    os.environ["OPENAI_API_KEY"] = "test_openai_key"
    os.environ["SERPAPI_KEY"] = "test_serp_key"
    
    # Create settings instance
    settings = Settings()
    
    # Test that values are loaded correctly
    assert settings.API_SECRET_KEY == "test_secret_key"
    assert settings.OPENAI_API_KEY == "test_openai_key"
    assert settings.SERPAPI_KEY == "test_serp_key"
    assert settings.OPENAI_MODEL == "gpt-4o-mini"  # Default value
    
def test_settings_creates_directories():
    """Test that Settings creates necessary directories."""
    settings = Settings()
    
    # Test that directories exist
    assert os.path.exists(settings.BASE_DATA_DIR)
    assert os.path.exists(settings.RAW_DATA_DIR)
    assert os.path.exists(settings.JSON_INPUTS_DIR)
    assert os.path.exists(settings.LOGS_DIR)
    assert os.path.exists(settings.PROCESSED_DATA_DIR) 