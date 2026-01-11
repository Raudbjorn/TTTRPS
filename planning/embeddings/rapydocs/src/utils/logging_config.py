"""
Centralized logging configuration for the rapydocs project.
This eliminates duplicate logging.basicConfig calls across modules.
"""

import logging
import sys
from typing import Optional


_LOGGING_CONFIGURED = False


def setup_logging(level: int = logging.INFO, format_str: Optional[str] = None) -> None:
    """Configure logging for the entire application."""
    global _LOGGING_CONFIGURED
    
    if _LOGGING_CONFIGURED:
        return
    
    if format_str is None:
        format_str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    logging.basicConfig(
        level=level,
        format=format_str,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    _LOGGING_CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Get a logger with consistent configuration."""
    setup_logging()  # Ensure logging is configured
    return logging.getLogger(name)