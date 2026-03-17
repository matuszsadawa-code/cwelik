"""
Configuration utilities
"""

import config
from functools import lru_cache


@lru_cache()
def get_config():
    """
    Get configuration module
    
    Returns:
        module: Configuration module with all settings
    """
    return config
