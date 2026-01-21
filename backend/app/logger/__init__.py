"""
Logger module for AgenticStockLaw backend.

Usage:
    from app.logger import get_logger, AppLogger
    
    # Simple usage
    logger = get_logger(__name__)
    logger.info("Hello!")
    
    # Custom configuration
    logger = AppLogger(name="api", level=logging.DEBUG).get_logger()
"""

from .custom_logging import AppLogger, get_logger
from .handlers import ConsoleHandler, FileHandler

__all__ = [
    "AppLogger",
    "get_logger",
    "ConsoleHandler",
    "FileHandler",
]
