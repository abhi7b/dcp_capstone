"""
Unit tests for the logger module.
"""
import os
import logging
import pytest
from app.utils.logger import setup_logger, get_logger, configure_loggers

def test_setup_logger():
    """Test that setup_logger creates a logger with the expected configuration."""
    # Create a test logger
    logger = setup_logger("test_logger")
    
    # Test logger properties
    assert logger.name == "test_logger"
    assert logger.level == logging.INFO  # Default level
    assert len(logger.handlers) > 0  # Has at least one handler
    
    # Test console handler exists
    has_console_handler = any(
        isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler)
        for handler in logger.handlers
    )
    assert has_console_handler, "Logger should have a console handler"
    
    # Test logging a message
    logger.info("Test message from test_setup_logger")

def test_get_logger():
    """Test that get_logger returns an appropriate logger."""
    # Get a logger for a new component
    logger = get_logger("test_component")
    
    # Test logger properties
    assert logger.name == "test_component"
    assert logger.level == logging.INFO  # Default level
    
    # Test logging a message
    logger.info("Test message from test_get_logger")
    
    # Get a logger for an existing component
    db_logger = get_logger("db")
    assert db_logger.name == "db"
    
    # Test logging a message with db logger
    db_logger.info("Test message from db logger")

def test_configure_loggers():
    """Test that configure_loggers properly sets up file handlers."""
    # Create a temporary log directory
    temp_log_dir = os.path.join(os.path.expanduser("~"), "temp_test_logs")
    os.makedirs(temp_log_dir, exist_ok=True)
    
    try:
        # Configure loggers
        configure_loggers(temp_log_dir)
        
        # Test logging with various loggers
        loggers = [
            get_logger("app"),
            get_logger("scraper"),
            get_logger("api"),
            get_logger("db"),
            get_logger("celery"),
            get_logger("scorer"),
            get_logger("nitter"),
            get_logger("nlp"),
            get_logger("processor"),
            get_logger("storage"),
            get_logger("person_processor"),
            get_logger("redis_service"),
            get_logger("test")
        ]
        
        # Log a test message with each logger
        for logger in loggers:
            logger.info(f"Test message from {logger.name} logger")
            
        # Check for file handler
        app_logger = get_logger("app")
        has_file_handler = any(
            isinstance(handler, logging.FileHandler)
            for handler in app_logger.handlers
        )
        assert has_file_handler, "Logger should have a file handler after configuration"
    finally:
        # Cleanup
        # Uncomment if you want to remove the temp directory after test
        # import shutil
        # shutil.rmtree(temp_log_dir, ignore_errors=True)
        pass 