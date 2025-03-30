import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from .config import settings

def setup_logger(name, log_file, level=logging.INFO):
    """Function to setup a logger with file and console handlers"""
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False
    
    # Remove existing handlers (for reconfiguration)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Create file handler if log file is provided
    if log_file:
        try:
            # Ensure log directory exists
            log_dir = os.path.dirname(log_file)
            os.makedirs(log_dir, exist_ok=True)
            
            # Create rotating file handler (10MB max size, keep 5 backups)
            file_handler = RotatingFileHandler(
                log_file, 
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            # Just log to console if file logging fails
            print(f"Warning: Could not set up file logging: {str(e)}")
            print(f"Continuing with console logging only")
    
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

# Create loggers for different components with console logging only initially
app_logger = setup_logger('app', None, level=log_level)
scraper_logger = setup_logger('scraper', None, level=log_level)
nitter_logger = setup_logger('nitter', None, level=log_level)
nlp_logger = setup_logger('nlp', None, level=log_level)
api_logger = setup_logger('api', None, level=log_level)
db_logger = setup_logger('db', None, level=log_level)
celery_logger = setup_logger('celery', None, level=log_level)

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
        nitter_logger = setup_logger('nitter', os.path.join(logs_dir, 'nitter.log'), level=log_level)
        nlp_logger = setup_logger('nlp', os.path.join(logs_dir, 'nlp.log'), level=log_level)
        api_logger = setup_logger('api', os.path.join(logs_dir, 'api.log'), level=log_level)
        db_logger = setup_logger('db', os.path.join(logs_dir, 'db.log'), level=log_level)
        celery_logger = setup_logger('celery', os.path.join(logs_dir, 'celery.log'), level=log_level)
        
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
        'celery': celery_logger
    }
    
    if name in known_loggers:
        return known_loggers[name]
    
    # Otherwise, create a new logger with console logging only
    # File logging will be configured later when configure_loggers is called
    return setup_logger(name, None, level=level) 