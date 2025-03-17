"""
Logging configuration for the DCP AI Scouting Platform.

This module provides a centralized logging configuration for the application,
with support for console and file logging, as well as structured logging.
"""
import logging
import logging.handlers
import os
import sys
from pathlib import Path
from datetime import datetime
import json
from typing import Dict, Any, Optional

from backend.config.config import settings

# Define log levels mapping
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

class LogManager:
    """Centralized logging manager for the application."""
    
    # Class variables
    _initialized = False
    _root_logger = None
    
    @classmethod
    def setup_logging(cls):
        """
        Set up the logging system.
        
        Returns:
            logging.Logger: The configured root logger
        """
        if cls._initialized:
            return cls._root_logger
        
        # Get settings
        log_level_str = settings.LOG_LEVEL
        log_format = settings.LOG_FORMAT
        file_enabled = settings.LOG_FILE_ENABLED
        file_path = settings.LOG_FILE_PATH
        
        # Convert log level string to logging constant
        log_level = LOG_LEVELS.get(log_level_str.upper(), logging.INFO)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        
        # Remove existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Add console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        
        # Choose formatter based on environment and format setting
        if log_format.lower() == 'json' and settings.ENV == 'production':
            # JSON formatter for structured logging in production
            formatter = logging.Formatter(
                '{"timestamp":"%(asctime)s", "level":"%(levelname)s", "name":"%(name)s", "message":"%(message)s"}'
            )
        else:
            # Simple formatter for development
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
            
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        # Add file handler if enabled
        if file_enabled:
            # Create logs directory if it doesn't exist
            log_dir = Path(file_path)
            log_dir.mkdir(exist_ok=True)
            
            # Single error log file for ERROR and CRITICAL logs
            error_log_file = log_dir / "error.log"
            error_handler = logging.handlers.RotatingFileHandler(
                error_log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(formatter)
            root_logger.addHandler(error_handler)
            
            # Only add app.log in development or if explicitly requested
            if settings.ENV != 'production' or settings.DEBUG:
                app_log_file = log_dir / "app.log"
                app_handler = logging.handlers.RotatingFileHandler(
                    app_log_file,
                    maxBytes=10*1024*1024,  # 10MB
                    backupCount=3,
                    encoding='utf-8'
                )
                app_handler.setLevel(log_level)
                app_handler.setFormatter(formatter)
                root_logger.addHandler(app_handler)
        
        # Mark as initialized
        cls._initialized = True
        cls._root_logger = root_logger
        
        # Log initialization
        root_logger.info(f"Logging initialized with level {log_level_str}")
        
        return root_logger
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        Get a logger with the specified name.
        
        Args:
            name: The name of the logger, typically __name__
            
        Returns:
            logging.Logger: A configured logger
        """
        if not cls._initialized:
            cls.setup_logging()
        
        return logging.getLogger(name)

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.
    
    Args:
        name: The name of the logger, typically __name__
        
    Returns:
        logging.Logger: A configured logger
    """
    return LogManager.get_logger(name)

def init_logging():
    """
    Initialize the logging system.
    
    Returns:
        logging.Logger: The configured root logger
    """
    return LogManager.setup_logging()

# Export commonly used functions and classes
__all__ = ["LogManager", "get_logger", "init_logging"]

# For testing/debugging
if __name__ == "__main__":
    LogManager.setup_logging()
    logger = get_logger("test")
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")
