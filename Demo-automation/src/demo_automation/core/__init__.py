"""
Core module for demo automation.

Contains configuration, errors, and base client classes.
"""

from .config import DemoConfiguration, FabricConfig, ExistingResourceAction
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
    "DemoAutomationError",
    "ConfigurationError",
    "FabricAPIError",
    "ValidationError",
]
