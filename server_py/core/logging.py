import logging
import sys
from functools import lru_cache

@lru_cache()
def get_logger(name: str):
    logger = logging.getLogger(name)
    
    # Check if handler already exists to avoid duplicate logs
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
    return logger
