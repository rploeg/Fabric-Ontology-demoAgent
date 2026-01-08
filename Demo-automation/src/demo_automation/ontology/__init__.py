"""
Ontology processing module.

Provides TTL to Fabric Ontology conversion functionality.

Components:
- ttl_converter: Parse TTL files and convert to Demo-automation format
- sdk_converter: Convert TTL results to SDK OntologyBuilder (recommended for new code)
"""

from .ttl_converter import (
    TTLToFabricConverter,
    parse_ttl_file,
    parse_ttl_content,
    ConversionResult,
    EntityType,
    RelationshipType,
    EntityTypeProperty,
)

# SDK Converter - bridges TTL converter output to SDK builders
from .sdk_converter import (
    ttl_to_sdk_builder,
    ttl_entity_to_sdk_info,
    ttl_relationship_to_sdk_info,
    ttl_result_to_sdk_infos,
    create_bridge_from_ttl,
)

__all__ = [
    # TTL Converter
    "TTLToFabricConverter",
    "parse_ttl_file",
    "parse_ttl_content",
    "ConversionResult",
    "EntityType",
    "RelationshipType",
    "EntityTypeProperty",
    
    # SDK Converter (recommended)
    "ttl_to_sdk_builder",
    "ttl_entity_to_sdk_info",
    "ttl_relationship_to_sdk_info",
    "ttl_result_to_sdk_infos",
    "create_bridge_from_ttl",
]
