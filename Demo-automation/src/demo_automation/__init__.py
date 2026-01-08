"""
Fabric Demo Automation Tool

Automated setup for Microsoft Fabric Ontology demos.
"""

__version__ = "0.1.0"

from .core.config import DemoConfiguration, FabricConfig
from .core.errors import (
    DemoAutomationError,
    ConfigurationError,
    FabricAPIError,
    ValidationError,
)
from .platform import (
    FabricClient,
    OneLakeDataClient,
    LakehouseClient,
    EventhouseClient,
)
from .orchestrator import DemoOrchestrator
from .validator import validate_demo_package, ValidationResult
from .state_manager import SetupStateManager
from .ontology import TTLToFabricConverter, parse_ttl_file, parse_ttl_content

# SDK Adapter for Fabric Ontology SDK integration
from .sdk_adapter import (
    create_sdk_client,
    create_ontology_builder,
    create_validator,
    map_ttl_type_to_sdk,
    map_ttl_type_to_string,
)

__all__ = [
    "__version__",
    "DemoConfiguration",
    "FabricConfig",
    "DemoAutomationError",
    "ConfigurationError",
    "FabricAPIError",
    "ValidationError",
    "FabricClient",
    "OneLakeDataClient",
    "LakehouseClient",
    "EventhouseClient",
    "DemoOrchestrator",
    "SetupStateManager",
    "validate_demo_package",
    "ValidationResult",
    "TTLToFabricConverter",
    "parse_ttl_file",
    "parse_ttl_content",
    # SDK adapter exports
    "create_sdk_client",
    "create_ontology_builder",
    "create_validator",
    "map_ttl_type_to_sdk",
    "map_ttl_type_to_string",
]
