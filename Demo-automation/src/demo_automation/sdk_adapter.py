"""
SDK Adapter Module.

Bridges Demo-automation with the Fabric Ontology SDK, providing:
- SDK client initialization from Demo-automation configuration
- Type conversion between TTL converter and SDK types
- Convenience wrappers for common SDK operations
"""

import logging
from typing import Optional, TYPE_CHECKING

from fabric_ontology import OntologyClient
from fabric_ontology.models import PropertyDataType
from fabric_ontology.builders import OntologyBuilder
from fabric_ontology.validation import OntologyValidator, validate_name, validate_data_type
from fabric_ontology.exceptions import ValidationError as SDKValidationError
from fabric_ontology.auth import (
    TokenProvider,
    InteractiveTokenProvider,
    ServicePrincipalTokenProvider,
    DeviceCodeTokenProvider,
)

if TYPE_CHECKING:
    from .core.config import DemoConfiguration


logger = logging.getLogger(__name__)


# =============================================================================
# Type Mapping: TTL Converter Types → SDK PropertyDataType
# =============================================================================

TTL_TO_SDK_TYPE_MAP = {
    # String types
    "String": PropertyDataType.STRING,
    "string": PropertyDataType.STRING,
    
    # Integer types (TTL uses various names)
    "BigInt": PropertyDataType.INT64,
    "Long": PropertyDataType.INT64,
    "Int": PropertyDataType.INT64,
    "Int64": PropertyDataType.INT64,
    "Integer": PropertyDataType.INT64,
    "int": PropertyDataType.INT64,
    "long": PropertyDataType.INT64,
    
    # Floating point types
    "Double": PropertyDataType.DOUBLE,
    "Float": PropertyDataType.DOUBLE,
    "double": PropertyDataType.DOUBLE,
    "float": PropertyDataType.DOUBLE,
    # Note: Decimal maps to Double because SDK rejects Decimal (returns NULL in Graph)
    "Decimal": PropertyDataType.DOUBLE,
    "decimal": PropertyDataType.DOUBLE,
    
    # Boolean
    "Boolean": PropertyDataType.BOOLEAN,
    "boolean": PropertyDataType.BOOLEAN,
    "bool": PropertyDataType.BOOLEAN,
    
    # DateTime types
    "DateTime": PropertyDataType.DATETIME,
    "datetime": PropertyDataType.DATETIME,
    "Date": PropertyDataType.DATETIME,
    "date": PropertyDataType.DATETIME,
    "DateTimeOffset": PropertyDataType.DATETIMEOFFSET,
}


def map_ttl_type_to_sdk(ttl_type: str) -> PropertyDataType:
    """
    Map a TTL converter type string to SDK PropertyDataType.
    
    Args:
        ttl_type: Type string from TTL converter (e.g., "String", "BigInt", "Double")
        
    Returns:
        Corresponding SDK PropertyDataType
        
    Note:
        - Unknown types default to STRING
        - Decimal is mapped to DOUBLE (Decimal returns NULL in Graph queries)
    """
    sdk_type = TTL_TO_SDK_TYPE_MAP.get(ttl_type)
    
    if sdk_type is None:
        logger.warning(f"Unknown TTL type '{ttl_type}', defaulting to String")
        return PropertyDataType.STRING
    
    if ttl_type.lower() == "decimal":
        logger.warning(
            f"Type 'Decimal' mapped to 'Double' - Decimal returns NULL in Graph queries"
        )
    
    return sdk_type


def map_ttl_type_to_string(ttl_type: str) -> str:
    """
    Map a TTL converter type string to SDK type string.
    
    Args:
        ttl_type: Type string from TTL converter
        
    Returns:
        SDK type string (e.g., "String", "Int64", "Double")
    """
    return map_ttl_type_to_sdk(ttl_type).value


# =============================================================================
# SDK Client Factory
# =============================================================================

def create_token_provider(config: "DemoConfiguration") -> TokenProvider:
    """
    Create an SDK TokenProvider from Demo-automation configuration.
    
    Args:
        config: Demo configuration containing Fabric connection details
        
    Returns:
        Configured TokenProvider instance (Interactive or ServicePrincipal)
    """
    tenant_id = config.fabric.tenant_id or "common"
    
    if config.fabric.use_interactive_auth:
        logger.info("Creating InteractiveTokenProvider for authentication")
        return InteractiveTokenProvider(tenant_id=tenant_id)
    else:
        # For non-interactive, we'd need service principal credentials
        # which would be added to config if needed
        logger.info("Creating InteractiveTokenProvider (fallback)")
        return InteractiveTokenProvider(tenant_id=tenant_id)


def create_sdk_client(config: "DemoConfiguration") -> OntologyClient:
    """
    Create an SDK OntologyClient from Demo-automation configuration.
    
    Args:
        config: Demo configuration containing Fabric connection details
        
    Returns:
        Configured OntologyClient instance
        
    Example:
        >>> from demo_automation.core.config import load_config
        >>> config = load_config("path/to/config.yaml")
        >>> client = create_sdk_client(config)
        >>> ontologies = client.list_ontologies()
    """
    # Create token provider based on config
    token_provider = create_token_provider(config)
    
    # Create and return SDK client
    client = OntologyClient(
        workspace_id=config.fabric.workspace_id,
        token_provider=token_provider,
    )
    
    logger.info(f"Created SDK client for workspace: {config.fabric.workspace_id}")
    return client


# =============================================================================
# SDK Builder Factory
# =============================================================================

def create_ontology_builder(seed: Optional[int] = None) -> OntologyBuilder:
    """
    Create an SDK OntologyBuilder instance.
    
    Args:
        seed: Optional seed for reproducible ID generation (useful for testing)
        
    Returns:
        New OntologyBuilder instance
    """
    return OntologyBuilder(seed=seed)


# =============================================================================
# SDK Validation Wrappers
# =============================================================================

def create_validator(strict: bool = True) -> OntologyValidator:
    """
    Create an SDK OntologyValidator instance.
    
    Args:
        strict: If True, treat warnings as errors
        
    Returns:
        New OntologyValidator instance
    """
    return OntologyValidator(strict=strict)


def validate_entity_name(name: str) -> None:
    """
    Validate an entity type name using SDK validation.
    
    Args:
        name: Entity type name to validate
        
    Raises:
        SDKValidationError: If name is invalid
    """
    validate_name(name, field_name="entityType")


def validate_property_name(name: str) -> None:
    """
    Validate a property name using SDK validation.
    
    Args:
        name: Property name to validate
        
    Raises:
        SDKValidationError: If name is invalid
    """
    validate_name(name, field_name="property")


def validate_relationship_name(name: str) -> None:
    """
    Validate a relationship type name using SDK validation.
    
    Args:
        name: Relationship type name to validate
        
    Raises:
        SDKValidationError: If name is invalid
    """
    validate_name(name, field_name="relationshipType")


def validate_sdk_data_type(data_type: str) -> None:
    """
    Validate a data type using SDK validation.
    
    Args:
        data_type: Data type string to validate
        
    Raises:
        SDKValidationError: If data type is invalid (includes Decimal check)
    """
    validate_data_type(data_type)


# =============================================================================
# Convenience Exports
# =============================================================================

__all__ = [
    # Type mapping
    "TTL_TO_SDK_TYPE_MAP",
    "map_ttl_type_to_sdk",
    "map_ttl_type_to_string",
    
    # Client/Builder factories
    "create_sdk_client",
    "create_token_provider",
    "create_ontology_builder",
    
    # Validation
    "create_validator",
    "validate_entity_name",
    "validate_property_name",
    "validate_relationship_name",
    "validate_sdk_data_type",
    
    # Re-exports from SDK for convenience
    "OntologyClient",
    "OntologyBuilder",
    "OntologyValidator",
    "PropertyDataType",
    "SDKValidationError",
    "TokenProvider",
    "InteractiveTokenProvider",
    "ServicePrincipalTokenProvider",
]
