"""
Unified MBED - Semantic embedding pipeline with hardware acceleration
"""

__version__ = "1.0.0-dev"
__author__ = "MBED Contributors"

from .core.config import MBEDSettings, get_settings, resolve_settings
from .core.hardware import HardwareDetector, HardwareType
from .core.logging import setup_logging, get_logger

__all__ = [
    "MBEDSettings",
    "get_settings", 
    "resolve_settings",
    "HardwareDetector",
    "HardwareType",
    "setup_logging",
    "get_logger",
]