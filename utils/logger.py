"""
Logger utility with proper formatting.
"""
import logging
import sys
from config import LOG_FORMAT, LOG_LEVEL


def setup_logger(name: str = "arbitrage_bot") -> logging.Logger:
    """
    Set up and configure logger instance.
    
    Args:
        name: Logger name
    
    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL.upper()))
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    
    # Formatter
    formatter = logging.Formatter(LOG_FORMAT)
    console_handler.setFormatter(formatter)
    
    # Add handler if not already added
    if not logger.handlers:
        logger.addHandler(console_handler)
    
    return logger
