"""
Fabric Demo Automation Tool

Automated setup for Microsoft Fabric Ontology demos.

SDK Integration (v0.2.0+):
    This package integrates with the Fabric Ontology SDK for ontology operations.
    Key SDK-integrated modules:
    
    - ``sdk_adapter``: Type mappings and SDK client/builder factories
    - ``binding.SDKBindingBridge``: SDK-based binding configuration builder
    - ``ontology.sdk_converter``: TTL to SDK OntologyBuilder conversion
    
    For new ontology projects, prefer using:
    - ``fabric_ontology.builders.OntologyBuilder`` for building definitions
    - ``fabric_ontology.validation.OntologyValidator`` for validation
"""

__version__ = "0.2.0"

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

# =============================================================================
# SDK Adapter for Fabric Ontology SDK integration
# =============================================================================
from .sdk_adapter import (
    create_sdk_client,
    create_ontology_builder,
    create_validator,
    map_ttl_type_to_sdk,
    map_ttl_type_to_string,
)

# SDK Converter for TTL to SDK builder conversion
from .ontology.sdk_converter import (
    ttl_to_sdk_builder,
    ttl_entity_to_sdk_info,
    ttl_relationship_to_sdk_info,
    create_bridge_from_ttl,
)

# SDK Binding Bridge (recommended for new code)
from .binding import (
    SDKBindingBridge,
    EntityBindingConfig,
    RelationshipContextConfig,
)

__all__ = [
    "__version__",
    # Core
    "DemoConfiguration",
    "FabricConfig",
    "DemoAutomationError",
    "ConfigurationError",
    "FabricAPIError",
    "ValidationError",
    # Platform clients
    "FabricClient",
    "OneLakeDataClient",
    "LakehouseClient",
    "EventhouseClient",
    # Orchestration
    "DemoOrchestrator",
    "SetupStateManager",
    # Validation
    "validate_demo_package",
    "ValidationResult",
    # TTL parsing
    "TTLToFabricConverter",
    "parse_ttl_file",
    "parse_ttl_content",
    # ==========================================================================
    # SDK Integration (v0.2.0+)
    # ==========================================================================
    # SDK adapter
    "create_sdk_client",
    "create_ontology_builder",
    "create_validator",
    "map_ttl_type_to_sdk",
    "map_ttl_type_to_string",
    # SDK converter
    "ttl_to_sdk_builder",
    "ttl_entity_to_sdk_info",
    "ttl_relationship_to_sdk_info",
    "create_bridge_from_ttl",
    # SDK binding bridge
    "SDKBindingBridge",
    "EntityBindingConfig",
    "RelationshipContextConfig",
]
