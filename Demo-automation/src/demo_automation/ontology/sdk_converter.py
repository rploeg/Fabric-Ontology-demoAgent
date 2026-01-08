"""
SDK Converter Module.

Converts TTL converter output to SDK OntologyBuilder calls.
This bridges the Demo-automation TTL parser with the Fabric Ontology SDK.

Key functions:
- ttl_to_sdk_builder: Convert ConversionResult to OntologyBuilder
- ttl_entity_to_sdk_info: Convert TTL EntityType to SDK TTLEntityInfo
- ttl_relationship_to_sdk_info: Convert TTL RelationshipType to SDK TTLRelationshipInfo
"""

import logging
from typing import Dict, List, Optional, Any

from fabric_ontology.builders import OntologyBuilder

from .ttl_converter import ConversionResult, EntityType, RelationshipType, EntityTypeProperty
from ..binding.sdk_binding_bridge import TTLEntityInfo, TTLRelationshipInfo
from ..sdk_adapter import map_ttl_type_to_string, TTL_TO_SDK_TYPE_MAP


logger = logging.getLogger(__name__)


# =============================================================================
# TTL Type to SDK Type Mapping
# =============================================================================

def _map_ttl_type(ttl_type: str) -> str:
    """
    Map TTL converter type to SDK PropertyDataType string.
    
    Args:
        ttl_type: Type string from TTL converter (String, BigInt, Double, etc.)
        
    Returns:
        SDK type string (String, Int64, Double, Boolean, DateTime, DateTimeOffset)
    """
    # Use the mapping from sdk_adapter
    return map_ttl_type_to_string(ttl_type)


# =============================================================================
# TTL Entity/Relationship to SDK Info Converters
# =============================================================================

def ttl_entity_to_sdk_info(ttl_entity: EntityType) -> TTLEntityInfo:
    """
    Convert a TTL EntityType to SDK TTLEntityInfo.
    
    Args:
        ttl_entity: Entity type from TTL conversion
        
    Returns:
        TTLEntityInfo ready for SDKBindingBridge
    """
    properties = []
    for prop in ttl_entity.properties:
        prop_dict = {
            "name": prop.name,
            "value_type": prop.value_type,
            "is_key": False,
        }
        # Mark key property based on key_property_name from TTL
        if ttl_entity.key_property_name:
            if prop.name.lower() == ttl_entity.key_property_name.lower():
                prop_dict["is_key"] = True
        properties.append(prop_dict)
    
    return TTLEntityInfo(
        name=ttl_entity.name,
        properties=properties,
        key_property_name=ttl_entity.key_property_name,
    )


def ttl_relationship_to_sdk_info(
    ttl_rel: RelationshipType,
    entity_id_to_name: Dict[str, str],
) -> Optional[TTLRelationshipInfo]:
    """
    Convert a TTL RelationshipType to SDK TTLRelationshipInfo.
    
    Args:
        ttl_rel: Relationship type from TTL conversion
        entity_id_to_name: Mapping of entity IDs to names
        
    Returns:
        TTLRelationshipInfo ready for SDKBindingBridge, or None if source/target unknown
    """
    source_name = entity_id_to_name.get(ttl_rel.source.entity_type_id)
    target_name = entity_id_to_name.get(ttl_rel.target.entity_type_id)
    
    if not source_name or not target_name:
        logger.warning(
            f"Cannot resolve relationship '{ttl_rel.name}': "
            f"source={ttl_rel.source.entity_type_id} ({source_name}), "
            f"target={ttl_rel.target.entity_type_id} ({target_name})"
        )
        return None
    
    return TTLRelationshipInfo(
        name=ttl_rel.name,
        source_entity_name=source_name,
        target_entity_name=target_name,
    )


# =============================================================================
# Full TTL to SDK Builder Conversion
# =============================================================================

def ttl_to_sdk_builder(
    conversion_result: ConversionResult,
    seed: Optional[int] = None,
) -> OntologyBuilder:
    """
    Convert TTL conversion result to SDK OntologyBuilder.
    
    Creates entity and relationship types WITHOUT bindings.
    Bindings should be added separately via SDKBindingBridge.
    
    Args:
        conversion_result: Result from TTL converter
        seed: Optional seed for reproducible ID generation
        
    Returns:
        OntologyBuilder with entity and relationship types configured
        
    Example:
        >>> result = parse_ttl_file("ontology.ttl")
        >>> builder = ttl_to_sdk_builder(result)
        >>> definition = builder.build()
    """
    builder = OntologyBuilder(seed=seed)
    
    # Map TTL entity IDs to names for relationship resolution
    entity_id_to_name = {e.id: e.name for e in conversion_result.entity_types}
    
    # Add entity types
    for ttl_entity in conversion_result.entity_types:
        entity_builder = builder.add_entity_type(ttl_entity.name)
        
        for prop in ttl_entity.properties:
            sdk_type = _map_ttl_type(prop.value_type)
            
            # Mark as key if matches TTL key_property_name
            is_key = (
                ttl_entity.key_property_name and
                prop.name.lower() == ttl_entity.key_property_name.lower()
            )
            
            entity_builder.add_property(
                name=prop.name,
                data_type=sdk_type,
                is_key=is_key,
                description=prop.description if prop.description else None,
            )
        
        entity_builder.done()
        logger.debug(f"Added entity type: {ttl_entity.name}")
    
    # Add relationship types
    for ttl_rel in conversion_result.relationship_types:
        source_name = entity_id_to_name.get(ttl_rel.source.entity_type_id)
        target_name = entity_id_to_name.get(ttl_rel.target.entity_type_id)
        
        if source_name and target_name:
            builder.add_relationship_type(
                ttl_rel.name,
                source_name,
                target_name,
            ).done()
            logger.debug(f"Added relationship type: {ttl_rel.name} ({source_name} -> {target_name})")
        else:
            logger.warning(
                f"Skipping relationship '{ttl_rel.name}': could not resolve "
                f"source ({ttl_rel.source.entity_type_id}) or target ({ttl_rel.target.entity_type_id})"
            )
    
    logger.info(
        f"Built SDK ontology: {len(conversion_result.entity_types)} entities, "
        f"{len(conversion_result.relationship_types)} relationships"
    )
    
    return builder


def ttl_result_to_sdk_infos(
    conversion_result: ConversionResult,
) -> tuple[List[TTLEntityInfo], List[TTLRelationshipInfo]]:
    """
    Convert TTL ConversionResult to lists of SDK info objects.
    
    This is useful for SDKBindingBridge which takes TTLEntityInfo and TTLRelationshipInfo.
    
    Args:
        conversion_result: Result from TTL converter
        
    Returns:
        Tuple of (entity_infos, relationship_infos)
    """
    # Map TTL entity IDs to names for relationship resolution
    entity_id_to_name = {e.id: e.name for e in conversion_result.entity_types}
    
    # Convert entities
    entity_infos = [
        ttl_entity_to_sdk_info(ttl_entity)
        for ttl_entity in conversion_result.entity_types
    ]
    
    # Convert relationships
    relationship_infos = []
    for ttl_rel in conversion_result.relationship_types:
        rel_info = ttl_relationship_to_sdk_info(ttl_rel, entity_id_to_name)
        if rel_info:
            relationship_infos.append(rel_info)
    
    return entity_infos, relationship_infos


# =============================================================================
# Integration with Binding Bridge
# =============================================================================

def create_bridge_from_ttl(
    conversion_result: ConversionResult,
    workspace_id: str,
    lakehouse_id: Optional[str] = None,
    eventhouse_id: Optional[str] = None,
    database_name: Optional[str] = None,
    cluster_uri: Optional[str] = None,
    seed: Optional[int] = None,
):
    """
    Create an SDKBindingBridge pre-populated with TTL entity and relationship types.
    
    This is a convenience function that:
    1. Converts TTL results to SDK info objects
    2. Creates an SDKBindingBridge
    3. Adds all entity types (without bindings)
    
    Bindings should be added separately by calling add_entity_with_binding
    or by directly calling bind_to_lakehouse/bind_to_eventhouse methods.
    
    Args:
        conversion_result: Result from TTL converter
        workspace_id: Fabric workspace ID
        lakehouse_id: Optional Lakehouse item ID
        eventhouse_id: Optional Eventhouse item ID
        database_name: Optional KQL database name
        cluster_uri: Optional Eventhouse cluster URI
        seed: Optional seed for reproducible ID generation
        
    Returns:
        SDKBindingBridge with entity/relationship types (no bindings yet)
    """
    from ..binding.sdk_binding_bridge import SDKBindingBridge
    
    bridge = SDKBindingBridge(
        workspace_id=workspace_id,
        lakehouse_id=lakehouse_id,
        eventhouse_id=eventhouse_id,
        database_name=database_name,
        cluster_uri=cluster_uri,
        seed=seed,
    )
    
    # Map TTL entity IDs to names for relationship resolution
    entity_id_to_name = {e.id: e.name for e in conversion_result.entity_types}
    
    # Add entities (without bindings - bindings added separately)
    for ttl_entity in conversion_result.entity_types:
        sdk_info = ttl_entity_to_sdk_info(ttl_entity)
        bridge.add_entity_type(
            name=sdk_info.name,
            properties=sdk_info.properties,
            key_property_name=sdk_info.key_property_name,
        )
    
    # Complete all entities before adding relationships
    bridge.complete_all_entities()
    
    # Add relationships (without contextualizations - added separately)
    for ttl_rel in conversion_result.relationship_types:
        source_name = entity_id_to_name.get(ttl_rel.source.entity_type_id)
        target_name = entity_id_to_name.get(ttl_rel.target.entity_type_id)
        
        if source_name and target_name:
            rel_builder = bridge.add_relationship_type(
                name=ttl_rel.name,
                source_entity=source_name,
                target_entity=target_name,
            )
            rel_builder.done()
    
    logger.info(
        f"Created SDK bridge from TTL: {len(conversion_result.entity_types)} entities, "
        f"{len(conversion_result.relationship_types)} relationships"
    )
    
    return bridge


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Main conversion functions
    "ttl_to_sdk_builder",
    "ttl_result_to_sdk_infos",
    
    # Individual converters
    "ttl_entity_to_sdk_info",
    "ttl_relationship_to_sdk_info",
    
    # Integration helper
    "create_bridge_from_ttl",
]
