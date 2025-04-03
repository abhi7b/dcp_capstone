"""
Logger configuration for the Duke VC Insight Engine.
"""
import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from .config import settings

def setup_logger(name: str, log_file: str = None, level: str = None) -> logging.Logger:
    """Set up a logger with file and console handlers
    
    Args:
        name: Logger name
        log_file: Optional path to log file. If None, only console logging is used
        level: Optional log level. If None, uses level from settings
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

# Create loggers for each service
nitter_logger = setup_logger('nitter', 'nitter.log')
nlp_logger = setup_logger('nlp', 'nlp.log')
scorer_logger = setup_logger('scorer', 'scorer.log')
processor_logger = setup_logger('processor', 'processor.log')
app_logger = setup_logger('app', 'app.log')
scraper_logger = setup_logger('scraper', 'scraper.log')
api_logger = setup_logger('api', 'api.log')
db_logger = setup_logger('db', 'db.log')
storage_logger = setup_logger('storage', 'storage.log')
person_processor_logger = setup_logger('person_processor', 'person_processor.log')

# Export all loggers
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
    'person_processor_logger'
]

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

# Create loggers for different components with console logging only initially
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
# Track if loggers have been reconfigured
_loggers_configured = False

# Function to reconfigure loggers with proper file paths
def configure_loggers(logs_dir):
    """Configure loggers with proper file paths once the application has set up directories"""
    global _loggers_configured
    if _loggers_configured:
        return
    
    try:
        # Ensure directory exists
        os.makedirs(logs_dir, exist_ok=True)
        
        # Reconfigure each logger
        app_logger = setup_logger('app', os.path.join(logs_dir, 'app.log'), level=log_level)
        scraper_logger = setup_logger('scraper', os.path.join(logs_dir, 'scraper.log'), level=log_level)
        api_logger = setup_logger('api', os.path.join(logs_dir, 'api.log'), level=log_level)
        db_logger = setup_logger('db', os.path.join(logs_dir, 'db.log'), level=log_level)
        celery_logger = setup_logger('celery', os.path.join(logs_dir, 'celery.log'), level=log_level)
        scorer_logger = setup_logger('scorer', os.path.join(logs_dir, 'scorer.log'), level=log_level)
        nitter_logger = setup_logger('nitter', os.path.join(logs_dir, 'nitter.log'), level=log_level)
        nlp_logger = setup_logger('nlp', os.path.join(logs_dir, 'nlp.log'), level=log_level)
        processor_logger = setup_logger('processor', os.path.join(logs_dir, 'processor.log'), level=log_level)
        storage_logger = setup_logger('storage', os.path.join(logs_dir, 'storage.log'), level=log_level)
        person_processor_logger = setup_logger('person_processor', os.path.join(logs_dir, 'person_processor.log'), level=log_level)

        app_logger.info(f"Loggers configured with directory: {logs_dir}")
        _loggers_configured = True
    except Exception as e:
        print(f"Failed to configure loggers with directory {logs_dir}: {str(e)}")

# Add simple get_logger function for new components
def get_logger(name, level=None):
    """Get a logger for a component, either existing or create new one"""
    if level is None:
        level = log_level
        
    # If it's a known component, return the existing logger
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
        'person_processor': person_processor_logger
    }
    
    if name in known_loggers:
        return known_loggers[name]
    
    # Otherwise, create a new logger with console logging only
    # File logging will be configured later when configure_loggers is called
    return setup_logger(name, None, level=level) 