"""
Core module for demo automation.

Contains configuration, errors, and base client classes.
"""

from .config import DemoConfiguration, FabricConfig, ExistingResourceAction
from .global_config import GlobalConfig, get_config_file_path, config_file_exists
from .errors import (
    DemoAutomationError,
    ConfigurationError,
    FabricAPIError,
    ValidationError,
)

__all__ = [
    "DemoConfiguration",
    "FabricConfig",
    "ExistingResourceAction",
    "GlobalConfig",
    "get_config_file_path",
    "config_file_exists",
    "DemoAutomationError",
    "ConfigurationError",
    "FabricAPIError",
    "ValidationError",
]
