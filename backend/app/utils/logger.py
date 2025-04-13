"""
Logger Configuration Module

Provides centralized logging configuration for all backend services.
Supports both file and console logging with different formatters.

Key Features:
- Configurable log levels
- File and console output
- Service-specific loggers
- Automatic directory creation
- Rotating file handlers
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from .config import settings

def setup_logger(name: str, log_file: str = None, level: str = None) -> logging.Logger:
    """
    Set up a logger with file and console handlers.
    
    Args:
        name: Logger name (e.g., 'redis_service', 'nitter_scraper')
        log_file: Optional path to log file. If None, only console logging is used
        level: Optional log level. If None, uses level from settings
        
    Returns:
        Configured logger instance
        
    Note:
        File handlers are only added when log_file is provided and
        will be configured later when configure_loggers() is called.
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:  # Only add handlers if they don't exist
        # Use provided level or fall back to settings
        log_level = level or settings.LOG_LEVEL
        logger.setLevel(log_level)
        
        # Create formatters
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_formatter = logging.Formatter(
            '%(levelname)s - %(message)s'
        )
        
        # Always add console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # Add file handler if log_file is provided
        if log_file:
            os.makedirs(settings.LOGS_DIR, exist_ok=True)
            file_handler = logging.FileHandler(
                os.path.join(settings.LOGS_DIR, log_file)
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
    
    return logger

# Get log level from environment or settings
log_level_name = os.environ.get("LOG_LEVEL", "INFO")
log_level = getattr(logging, log_level_name)

# Use a safe temporary directory in the user's home folder
temp_log_dir = os.path.join(os.path.expanduser("~"), "temp_duke_vc_logs")
try:
    os.makedirs(temp_log_dir, exist_ok=True)
except Exception:
    # If we can't create the temp directory, just use console logging initially
    temp_log_dir = None

# Initialize service loggers with console logging only
app_logger = setup_logger('app', None, level=log_level)
scraper_logger = setup_logger('scraper', None, level=log_level)
api_logger = setup_logger('api', None, level=log_level)
db_logger = setup_logger('db', None, level=log_level)
celery_logger = setup_logger('celery', None, level=log_level)
scorer_logger = setup_logger('scorer', None, level=log_level)
nitter_logger = setup_logger('nitter', None, level=log_level)
nlp_logger = setup_logger('nlp', None, level=log_level)
processor_logger = setup_logger('processor', None, level=log_level)
storage_logger = setup_logger('storage', None, level=log_level)
person_processor_logger = setup_logger('person_processor', None, level=log_level)
redis_service_logger = setup_logger('redis_service', None, level=log_level)
test_logger = setup_logger('test', None, level=log_level)
# Track if loggers have been reconfigured
_loggers_configured = False

def configure_loggers(logs_dir):
    """
    Configure loggers with proper file paths.
    
    Args:
        logs_dir: Directory path for log files
        
    Note:
        This should be called once the application has set up directories.
        It will add file handlers to existing loggers.
    """
    global _loggers_configured
    if _loggers_configured:
        return
    
    try:
        # Ensure directory exists
        os.makedirs(logs_dir, exist_ok=True)
        
        # Reconfigure each logger with file handlers
        loggers_config = {
            'app': 'app.log',
            'scraper': 'scraper.log',
            'api': 'api.log',
            'db': 'db.log',
            'celery': 'celery.log',
            'scorer': 'scorer.log',
            'nitter': 'nitter.log',
            'nlp': 'nlp.log',
            'processor': 'processor.log',
            'storage': 'storage.log',
            'person_processor': 'person_processor.log',
            'redis_service': 'redis_service.log',
            'test': 'test.log',
        }
        
        for name, log_file in loggers_config.items():
            setup_logger(name, os.path.join(logs_dir, log_file), level=log_level)
            
        app_logger.info(f"Loggers configured with directory: {logs_dir}")
        _loggers_configured = True
    except Exception as e:
        print(f"Failed to configure loggers with directory {logs_dir}: {str(e)}")

def get_logger(name: str, level: str = None) -> logging.Logger:
    """
    Get or create a logger for a component.
    
    Args:
        name: Logger name (e.g., 'redis_service', 'nitter_scraper')
        level: Optional log level override
        
    Returns:
        Logger instance (existing or new)
        
    Note:
        For known services, returns the pre-configured logger.
        For new services, creates a console-only logger.
    """
    if level is None:
        level = log_level
        
    # Known service loggers
    known_loggers = {
        'app': app_logger,
        'scraper': scraper_logger,
        'nitter': nitter_logger,
        'nlp': nlp_logger,
        'api': api_logger,
        'db': db_logger,
        'celery': celery_logger,
        'scorer': scorer_logger,
        'processor': processor_logger,
        'storage': storage_logger,
        'person_processor': person_processor_logger,
        'redis_service': redis_service_logger,
        'test': test_logger,
    }
    
    if name in known_loggers:
        return known_loggers[name]
    
    # Create new logger with console logging only
    return setup_logger(name, None, level=level)

# Export all loggers and utilities
__all__ = [
    'nitter_logger',
    'nlp_logger',
    'scorer_logger',
    'processor_logger',
    'app_logger',
    'scraper_logger',
    'api_logger',
    'db_logger',
    'storage_logger',
    'setup_logger',
    'person_processor_logger',
    'redis_service_logger',
    'get_logger',
    'configure_loggers',
    'test_logger'
] 