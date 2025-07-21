"""
Utility modules for the Proactive Work-Life Assistant

This package contains utility functions and classes for:
- Configuration management
- Logging setup and management
- Common helper functions
"""

from .config import Config
from .logger import setup_logger, log_function_call

__all__ = [
    'Config',
    'setup_logger', 
    'log_function_call'
]

__version__ = "1.0.0"