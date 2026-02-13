"""
SDK Adapter Module.

Bridges Demo-automation with the Unofficial Fabric Ontology SDK (v0.2.0+), providing:
- SDK client initialization from Demo-automation configuration
- Type conversion between TTL converter and SDK types
- Convenience wrappers for common SDK operations

SDK Reference: https://github.com/falloutxAY/Unofficial-Fabric-Ontology-SDK
"""

import logging
import os
from typing import Optional, TYPE_CHECKING

from fabric_ontology import FabricClient
from fabric_ontology.models import PropertyDataType
from fabric_ontology.builders import OntologyBuilder
from fabric_ontology.validation import OntologyValidator, validate_name, validate_data_type
from fabric_ontology.exceptions import (
    ValidationError as SDKValidationError,
    FabricOntologyError,
    AuthenticationError as SDKAuthenticationError,
    ApiError,
    ResourceNotFoundError as SDKResourceNotFoundError,
    RateLimitError as SDKRateLimitError,
    ConflictError,
)
try:
    from fabric_ontology.resilience import (
        RateLimiter as SDKRateLimiter,
        CircuitBreaker as SDKCircuitBreaker,
        CircuitBreakerOpenError as SDKCircuitBreakerOpenError,
    )
except ImportError:
    # fabric_ontology.resilience not available in SDK v0.4.0
    SDKRateLimiter = None
    SDKCircuitBreaker = None
    SDKCircuitBreakerOpenError = None

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
    "BigInt": PropertyDataType.BIGINT,
    "Long": PropertyDataType.BIGINT,
    "Int": PropertyDataType.BIGINT,
    "Int64": PropertyDataType.BIGINT,
    "Integer": PropertyDataType.BIGINT,
    "int": PropertyDataType.BIGINT,
    "long": PropertyDataType.BIGINT,
    
    # Floating point types
    "Double": PropertyDataType.DOUBLE,
    "Float": PropertyDataType.FLOAT,
    "double": PropertyDataType.DOUBLE,
    "float": PropertyDataType.FLOAT,
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
    "DateTimeOffset": PropertyDataType.DATETIME,
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

def create_sdk_client(
    config: "DemoConfiguration",
    auth_method: Optional[str] = None,
) -> FabricClient:
    """
    Create an SDK FabricClient from Demo-automation configuration.
    
    Uses SDK v0.3.0+ factory methods for authentication:
    - from_interactive(): Interactive browser login (default)
    - from_service_principal(): Service principal credentials
    - from_azure_cli(): Azure CLI credentials (requires `az login`)
    - from_device_code(): Device code flow for headless environments
    
    Args:
        config: Demo configuration containing Fabric connection details
        auth_method: Override auth method. One of: "interactive", "service_principal", 
                     "azure_cli", "device_code", "default". If None, uses config value.
        
    Returns:
        Configured FabricClient instance
        
    Example:
        >>> from demo_automation.core.config import load_config
        >>> config = load_config("path/to/config.yaml")
        >>> client = create_sdk_client(config)
        >>> ontologies = client.ontologies.list(workspace_id)
    """
    # Determine auth method from config or override
    method = auth_method or getattr(config.fabric, 'auth_method', None) or "interactive"
    method = method.lower().replace("-", "_")
    
    logger.info(f"Creating FabricClient with auth method: {method}")
    
    if method == "interactive":
        client = FabricClient.from_interactive()
        
    elif method == "service_principal":
        # Get credentials from environment variables
        tenant_id = config.fabric.tenant_id or os.environ.get("AZURE_TENANT_ID")
        client_id = os.environ.get("AZURE_CLIENT_ID")
        client_secret = os.environ.get("AZURE_CLIENT_SECRET")
        
        if not all([tenant_id, client_id, client_secret]):
            raise ValueError(
                "Service principal auth requires AZURE_TENANT_ID, AZURE_CLIENT_ID, "
                "and AZURE_CLIENT_SECRET environment variables"
            )
        
        client = FabricClient.from_service_principal(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
        )
        
    elif method == "azure_cli":
        client = FabricClient.from_azure_cli()
        
    elif method == "device_code":
        client = FabricClient.from_device_code()
        
    elif method == "default":
        # Uses DefaultAzureCredential chain
        client = FabricClient.from_azure_cli()  # Closest equivalent
        
    else:
        logger.warning(f"Unknown auth method '{method}', falling back to interactive")
        client = FabricClient.from_interactive()
    
    logger.info(f"Created FabricClient for workspace: {config.fabric.workspace_id}")
    return client


# Backwards compatibility alias
def create_token_provider(config: "DemoConfiguration"):
    """
    DEPRECATED: Use create_sdk_client() instead.
    
    This function is kept for backwards compatibility but will be removed
    in a future version. The SDK v0.3.0+ uses FabricClient.from_*() factory
    methods instead of TokenProvider classes.
    """
    import warnings
    warnings.warn(
        "create_token_provider() is deprecated. Use create_sdk_client() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    # Return the client itself as it handles auth internally
    return create_sdk_client(config)


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
    "create_token_provider",  # Deprecated, kept for backwards compatibility
    "create_ontology_builder",
    
    # Validation
    "create_validator",
    "validate_entity_name",
    "validate_property_name",
    "validate_relationship_name",
    "validate_sdk_data_type",
    
    # Re-exports from SDK for convenience
    "FabricClient",
    "OntologyBuilder",
    "OntologyValidator",
    "PropertyDataType",
    "SDKValidationError",
    
    # SDK Resilience (for rate limiting and circuit breaker)
    "SDKRateLimiter",
    "SDKCircuitBreaker",
    "SDKCircuitBreakerOpenError",
    
    # SDK Exceptions (for error handling)
    "FabricOntologyError",
    "SDKAuthenticationError",
    "ApiError",
    "SDKResourceNotFoundError",
    "SDKRateLimitError",
    "ConflictError",
]
