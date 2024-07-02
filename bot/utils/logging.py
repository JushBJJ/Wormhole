import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logging(log_file: str = 'logs/wormhole.log', log_level: int = logging.INFO):
    logger = logging.getLogger('wormhole')
    logger.setLevel(log_level)

    # Create logs directory if it doesn't exist
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    # File handler
    file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
