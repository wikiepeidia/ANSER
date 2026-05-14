"""
Logging Configuration
Centralized logging setup for the application
"""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime

# Create logs directory
LOGS_DIR = Path(__file__).parent / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

# Log file paths
APP_LOG = LOGS_DIR / 'app.log'
ERROR_LOG = LOGS_DIR / 'error.log'
API_LOG = LOGS_DIR / 'api.log'


def setup_logging():
    """Configure logging for the entire application"""
    
    # Root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Clear existing handlers
    logger.handlers = []
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler (INFO and above)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler for all logs (rotating)
    file_handler = RotatingFileHandler(
        APP_LOG,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # File handler for errors only
    error_handler = RotatingFileHandler(
        ERROR_LOG,
        maxBytes=10*1024*1024,
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)
    
    return logger


def get_logger(name):
    """Get a logger for a specific module"""
    return logging.getLogger(name)


# API request logger
def log_api_request(endpoint, method, params=None, status_code=None, duration=None):
    """Log API requests"""
    logger = get_logger('api')
    log_msg = f"{method} {endpoint}"
    
    if params:
        log_msg += f" | Params: {params}"
    if status_code:
        log_msg += f" | Status: {status_code}"
    if duration:
        log_msg += f" | Duration: {duration:.2f}ms"
    
    logger.info(log_msg)
