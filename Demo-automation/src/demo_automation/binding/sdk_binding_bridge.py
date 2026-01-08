"""
SDK Binding Bridge Module.

Bridges parsed binding configurations from Demo-automation to SDK builders.
This module replaces the custom OntologyBindingBuilder with SDK builders
for entity bindings and relationship contextualizations.

Key functions:
- SDKBindingBridge: Main bridge class for building ontologies with bindings
- EntityBindingConfig: Unified configuration for entity bindings
- RelationshipContextConfig: Unified configuration for relationship contextualizations
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union

from fabric_ontology.builders import OntologyBuilder, EntityTypeBuilder, RelationshipTypeBuilder
from fabric_ontology.models import PropertyDataType

from .binding_parser import ParsedEntityBinding, ParsedPropertyMapping

# Import ParsedRelationshipBinding from the main binding_builder module
# (it's also defined there for compatibility)
from .binding_builder import ParsedRelationshipBinding

from ..sdk_adapter import map_ttl_type_to_string, TTL_TO_SDK_TYPE_MAP


logger = logging.getLogger(__name__)


# =============================================================================
# Configuration Data Classes
# =============================================================================

@dataclass
class EntityBindingConfig:
    """
    Unified configuration for binding an entity type to a data source.
    
    Supports both Lakehouse (NonTimeSeries) and Eventhouse (TimeSeries) bindings.
    An entity can have ONE static binding and MULTIPLE time-series bindings.
    """
    entity_name: str
    binding_type: str  # "static" or "timeseries"
    table_name: str
    key_column: str
    column_mappings: Dict[str, str]  # property_name -> source_column
    timestamp_column: Optional[str] = None  # Required for timeseries
    database_name: Optional[str] = None  # Required for eventhouse
    cluster_uri: Optional[str] = None  # Required for eventhouse

    @classmethod
    def from_parsed(cls, parsed: ParsedEntityBinding) -> "EntityBindingConfig":
        """Create from ParsedEntityBinding."""
        return cls(
            entity_name=parsed.entity_name,
            binding_type=parsed.binding_type.value,
            table_name=parsed.table_name,
            key_column=parsed.key_column,
            timestamp_column=parsed.timestamp_column,
            column_mappings={
                pm.target_property: pm.source_column
                for pm in parsed.property_mappings
            },
        )


@dataclass
class RelationshipContextConfig:
    """
    Configuration for contextualizing a relationship type.
    
    Contextualizations bind relationships to fact/bridge tables that contain
    foreign keys linking source and target entities.
    """
    relationship_name: str
    source_entity: str
    target_entity: str
    source_type: str  # "lakehouse" or "eventhouse"
    table_name: str
    source_key_column: str  # Column linking to source entity's key
    target_key_column: str  # Column linking to target entity's key
    database_name: Optional[str] = None  # For eventhouse

    @classmethod
    def from_parsed(cls, parsed: ParsedRelationshipBinding) -> "RelationshipContextConfig":
        """Create from ParsedRelationshipBinding."""
        return cls(
            relationship_name=parsed.relationship_name,
            source_entity=parsed.source_entity,
            target_entity=parsed.target_entity,
            source_type=parsed.source_type,
            table_name=parsed.table_name,
            source_key_column=parsed.source_key_column,
            target_key_column=parsed.target_key_column,
        )


@dataclass
class TTLEntityInfo:
    """
    Entity type information extracted from TTL conversion.
    
    This represents the minimal information needed from TTL
    to create entity types with SDK builders.
    """
    name: str
    properties: List[Dict[str, Any]]  # List of {name, value_type, is_key}
    key_property_name: Optional[str] = None


@dataclass
class TTLRelationshipInfo:
    """
    Relationship type information extracted from TTL conversion.
    
    Minimal information needed from TTL to create relationship types.
    """
    name: str
    source_entity_name: str
    target_entity_name: str


# =============================================================================
# SDK Binding Bridge
# =============================================================================

class SDKBindingBridge:
    """
    Bridge between Demo-automation parsed bindings and SDK OntologyBuilder.
    
    This class orchestrates the creation of an ontology definition using SDK builders,
    combining entity/relationship type definitions with their data bindings.
    
    Usage:
        bridge = SDKBindingBridge(
            workspace_id="...",
            lakehouse_id="...",
            eventhouse_id="...",
            database_name="...",
            cluster_uri="...",
        )
        
        # Add entities with their bindings
        for entity_info, binding_config in entity_data:
            bridge.add_entity_with_binding(entity_info, binding_config)
        
        # Add relationships with contextualizations
        for rel_info, context_config in relationship_data:
            bridge.add_relationship_with_context(rel_info, context_config)
        
        # Build the final definition
        definition = bridge.build()
    """

    def __init__(
        self,
        workspace_id: str,
        lakehouse_id: Optional[str] = None,
        eventhouse_id: Optional[str] = None,
        database_name: Optional[str] = None,
        cluster_uri: Optional[str] = None,
        seed: Optional[int] = None,
    ):
        """
        Initialize the SDK binding bridge.
        
        Args:
            workspace_id: Fabric workspace ID
            lakehouse_id: Lakehouse item ID for static bindings
            eventhouse_id: Eventhouse item ID for time-series bindings
            database_name: KQL database name (required for eventhouse)
            cluster_uri: Eventhouse cluster URI (required for eventhouse)
            seed: Optional seed for reproducible ID generation
        """
        self.workspace_id = workspace_id
        self.lakehouse_id = lakehouse_id
        self.eventhouse_id = eventhouse_id
        self.database_name = database_name
        self.cluster_uri = cluster_uri
        
        # Create SDK builder
        self._builder = OntologyBuilder(seed=seed)
        
        # Track entity builders for relationship resolution
        self._entity_builders: Dict[str, EntityTypeBuilder] = {}
        self._completed_entities: List[str] = []
        
        logger.debug(f"SDKBindingBridge initialized for workspace {workspace_id}")

    def add_entity_type(
        self,
        name: str,
        properties: List[Dict[str, Any]],
        key_property_name: Optional[str] = None,
    ) -> EntityTypeBuilder:
        """
        Add an entity type to the ontology.
        
        Args:
            name: Entity type name
            properties: List of property definitions [{name, value_type, is_key?}]
            key_property_name: Name of the key property (alternative to is_key in properties)
            
        Returns:
            EntityTypeBuilder for further configuration
        """
        entity_builder = self._builder.add_entity_type(name)
        
        for prop in properties:
            prop_name = prop.get("name")
            value_type = prop.get("value_type", "String")
            is_key = prop.get("is_key", False)
            
            # Check if this is the key property by name
            if key_property_name and prop_name.lower() == key_property_name.lower():
                is_key = True
            
            # Map TTL type to SDK type
            sdk_type = map_ttl_type_to_string(value_type)
            
            entity_builder.add_property(prop_name, sdk_type, is_key=is_key)
        
        self._entity_builders[name] = entity_builder
        logger.debug(f"Added entity type: {name} with {len(properties)} properties")
        return entity_builder

    def add_entity_with_binding(
        self,
        ttl_entity: TTLEntityInfo,
        binding: EntityBindingConfig,
    ) -> EntityTypeBuilder:
        """
        Add an entity type from TTL info with data binding.
        
        This is the primary method for adding entities with their bindings.
        It combines TTL-derived entity definition with binding configuration.
        
        Args:
            ttl_entity: Entity type information from TTL conversion
            binding: Binding configuration from parsed binding files
            
        Returns:
            EntityTypeBuilder for further configuration
        """
        # Create entity type
        entity_builder = self.add_entity_type(
            name=ttl_entity.name,
            properties=ttl_entity.properties,
            key_property_name=ttl_entity.key_property_name,
        )
        
        # Add appropriate binding
        if binding.binding_type == "static" and self.lakehouse_id:
            self._add_lakehouse_binding(entity_builder, binding)
        elif binding.binding_type == "timeseries" and self.eventhouse_id:
            self._add_eventhouse_binding(entity_builder, binding)
        else:
            logger.warning(
                f"Cannot add binding for {ttl_entity.name}: "
                f"type={binding.binding_type}, lakehouse_id={self.lakehouse_id}, eventhouse_id={self.eventhouse_id}"
            )
        
        return entity_builder

    def _add_lakehouse_binding(
        self,
        entity_builder: EntityTypeBuilder,
        binding: EntityBindingConfig,
    ) -> None:
        """Add a Lakehouse (static) binding to an entity."""
        if not self.lakehouse_id:
            raise ValueError("lakehouse_id required for static binding")
        
        entity_builder.bind_to_lakehouse(
            workspace_id=self.workspace_id,
            lakehouse_id=self.lakehouse_id,
            table_name=binding.table_name,
            column_mappings=binding.column_mappings,
            source_schema="dbo",  # Default schema for Lakehouses
        )
        logger.debug(f"Added Lakehouse binding to {entity_builder._name}: {binding.table_name}")

    def _add_eventhouse_binding(
        self,
        entity_builder: EntityTypeBuilder,
        binding: EntityBindingConfig,
    ) -> None:
        """Add an Eventhouse (timeseries) binding to an entity."""
        if not self.eventhouse_id or not self.database_name:
            raise ValueError("eventhouse_id and database_name required for timeseries binding")
        if not self.cluster_uri:
            raise ValueError("cluster_uri required for eventhouse binding")
        if not binding.timestamp_column:
            raise ValueError(f"timestamp_column required for timeseries binding on {entity_builder._name}")
        
        # Find key properties for static_key_properties
        key_props = [
            prop.name for prop in entity_builder._properties 
            if prop.id in entity_builder._key_property_ids
        ]
        
        entity_builder.bind_to_eventhouse(
            workspace_id=self.workspace_id,
            eventhouse_id=self.eventhouse_id,
            database_name=self.database_name,
            table_name=binding.table_name,
            cluster_uri=self.cluster_uri,
            timestamp_column=binding.timestamp_column,
            column_mappings=binding.column_mappings,
            static_key_properties=key_props if key_props else None,
        )
        logger.debug(f"Added Eventhouse binding to {entity_builder._name}: {binding.table_name}")

    def complete_entity(self, entity_name: str) -> None:
        """
        Complete entity configuration and add to ontology.
        
        Call this after all properties and bindings are configured.
        """
        if entity_name not in self._entity_builders:
            raise ValueError(f"Entity '{entity_name}' not found in builders")
        if entity_name in self._completed_entities:
            logger.warning(f"Entity '{entity_name}' already completed")
            return
        
        self._entity_builders[entity_name].done()
        self._completed_entities.append(entity_name)
        logger.debug(f"Completed entity: {entity_name}")

    def complete_all_entities(self) -> None:
        """Complete all pending entity configurations."""
        for name in list(self._entity_builders.keys()):
            if name not in self._completed_entities:
                self.complete_entity(name)

    def add_relationship_type(
        self,
        name: str,
        source_entity: str,
        target_entity: str,
    ) -> RelationshipTypeBuilder:
        """
        Add a relationship type to the ontology.
        
        Args:
            name: Relationship type name
            source_entity: Name of the source entity type
            target_entity: Name of the target entity type
            
        Returns:
            RelationshipTypeBuilder for further configuration
        """
        # Ensure entities are completed before adding relationships
        if source_entity not in self._completed_entities:
            self.complete_entity(source_entity)
        if target_entity not in self._completed_entities:
            self.complete_entity(target_entity)
        
        rel_builder = self._builder.add_relationship_type(name, source_entity, target_entity)
        logger.debug(f"Added relationship type: {name} ({source_entity} -> {target_entity})")
        return rel_builder

    def add_relationship_with_context(
        self,
        ttl_relationship: TTLRelationshipInfo,
        context: RelationshipContextConfig,
    ) -> RelationshipTypeBuilder:
        """
        Add a relationship type with contextualization binding.
        
        Args:
            ttl_relationship: Relationship type information from TTL conversion
            context: Contextualization configuration from parsed binding files
            
        Returns:
            RelationshipTypeBuilder for further configuration
        """
        rel_builder = self.add_relationship_type(
            name=ttl_relationship.name,
            source_entity=ttl_relationship.source_entity_name,
            target_entity=ttl_relationship.target_entity_name,
        )
        
        # Add contextualization
        if context.source_type == "lakehouse" and self.lakehouse_id:
            rel_builder.contextualize_from_lakehouse(
                workspace_id=self.workspace_id,
                lakehouse_id=self.lakehouse_id,
                table_name=context.table_name,
                source_key_columns=context.source_key_column,
                target_key_columns=context.target_key_column,
                source_schema="dbo",
            )
            logger.debug(f"Added Lakehouse contextualization to {ttl_relationship.name}")
        elif context.source_type == "eventhouse" and self.eventhouse_id:
            rel_builder.contextualize_from_eventhouse(
                workspace_id=self.workspace_id,
                eventhouse_id=self.eventhouse_id,
                database_name=context.database_name or self.database_name,
                table_name=context.table_name,
                source_key_columns=context.source_key_column,
                target_key_columns=context.target_key_column,
            )
            logger.debug(f"Added Eventhouse contextualization to {ttl_relationship.name}")
        else:
            logger.warning(
                f"Cannot add contextualization for {ttl_relationship.name}: "
                f"source_type={context.source_type}, lakehouse_id={self.lakehouse_id}"
            )
        
        return rel_builder

    def add_relationship_contextualization_only(
        self,
        relationship_name: str,
        source_entity: str,
        target_entity: str,
        context: RelationshipContextConfig,
    ) -> RelationshipTypeBuilder:
        """
        Add a relationship type with contextualization using only config data.
        
        Use this when you don't have TTL relationship info but have binding config.
        
        Args:
            relationship_name: Name of the relationship type
            source_entity: Name of the source entity type
            target_entity: Name of the target entity type
            context: Contextualization configuration
            
        Returns:
            RelationshipTypeBuilder for further configuration
        """
        ttl_rel = TTLRelationshipInfo(
            name=relationship_name,
            source_entity_name=source_entity,
            target_entity_name=target_entity,
        )
        return self.add_relationship_with_context(ttl_rel, context)

    def build(self):
        """
        Build the complete ontology definition.
        
        Returns:
            OntologyDefinition with all entities, relationships, bindings, and contextualizations
        """
        # Complete any remaining entities
        self.complete_all_entities()
        
        definition = self._builder.build()
        logger.info(
            f"Built ontology definition: {len(definition.entity_types)} entities, "
            f"{len(definition.relationship_types)} relationships"
        )
        return definition

    def get_builder(self) -> OntologyBuilder:
        """Get the underlying SDK OntologyBuilder."""
        return self._builder


# =============================================================================
# Convenience Functions
# =============================================================================

def create_binding_bridge(
    workspace_id: str,
    lakehouse_id: Optional[str] = None,
    eventhouse_id: Optional[str] = None,
    database_name: Optional[str] = None,
    cluster_uri: Optional[str] = None,
    seed: Optional[int] = None,
) -> SDKBindingBridge:
    """
    Factory function to create an SDKBindingBridge.
    
    Args:
        workspace_id: Fabric workspace ID
        lakehouse_id: Optional Lakehouse item ID
        eventhouse_id: Optional Eventhouse item ID
        database_name: Optional KQL database name
        cluster_uri: Optional Eventhouse cluster URI
        seed: Optional seed for reproducible ID generation
        
    Returns:
        Configured SDKBindingBridge instance
    """
    return SDKBindingBridge(
        workspace_id=workspace_id,
        lakehouse_id=lakehouse_id,
        eventhouse_id=eventhouse_id,
        database_name=database_name,
        cluster_uri=cluster_uri,
        seed=seed,
    )


def bridge_parsed_entity_to_config(
    parsed: ParsedEntityBinding,
    database_name: Optional[str] = None,
    cluster_uri: Optional[str] = None,
) -> EntityBindingConfig:
    """
    Convert a ParsedEntityBinding to EntityBindingConfig.
    
    Args:
        parsed: Parsed entity binding from markdown/YAML
        database_name: Database name for eventhouse bindings
        cluster_uri: Cluster URI for eventhouse bindings
        
    Returns:
        EntityBindingConfig ready for SDKBindingBridge
    """
    config = EntityBindingConfig.from_parsed(parsed)
    if config.binding_type == "timeseries":
        config.database_name = database_name
        config.cluster_uri = cluster_uri
    return config


def bridge_parsed_relationship_to_config(
    parsed: ParsedRelationshipBinding,
    database_name: Optional[str] = None,
) -> RelationshipContextConfig:
    """
    Convert a ParsedRelationshipBinding to RelationshipContextConfig.
    
    Args:
        parsed: Parsed relationship binding from markdown/YAML
        database_name: Database name for eventhouse contextualizations
        
    Returns:
        RelationshipContextConfig ready for SDKBindingBridge
    """
    config = RelationshipContextConfig.from_parsed(parsed)
    if config.source_type == "eventhouse":
        config.database_name = database_name
    return config


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Main bridge class
    "SDKBindingBridge",
    
    # Configuration classes
    "EntityBindingConfig",
    "RelationshipContextConfig",
    "TTLEntityInfo",
    "TTLRelationshipInfo",
    
    # Factory functions
    "create_binding_bridge",
    "bridge_parsed_entity_to_config",
    "bridge_parsed_relationship_to_config",
]
