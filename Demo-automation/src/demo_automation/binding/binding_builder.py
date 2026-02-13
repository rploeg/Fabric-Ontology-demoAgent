"""
Ontology Binding Builder for configuring data source bindings.

Builds the binding configuration that connects ontology entities to
Lakehouse tables (NonTimeSeries) and Eventhouse tables (TimeSeries),
as well as relationship contextualizations between entities.

.. deprecated:: 0.2.0
    This module is deprecated in favor of the SDK Binding Bridge.
    Use ``sdk_binding_bridge.SDKBindingBridge`` instead, which provides:
    - Official Fabric Ontology SDK integration
    - Built-in validation and type safety
    - Cleaner fluent builder API
    
    Migration example:
    
    Old (deprecated):
        builder = OntologyBindingBuilder(workspace_id, ontology_id)
        builder.add_lakehouse_binding(entity_id, lakehouse_id, table, key, mappings)
        parts = builder.build_definition_parts()
    
    New (recommended):
        from demo_automation.binding import SDKBindingBridge
        bridge = SDKBindingBridge(workspace_id, lakehouse_id=lakehouse_id)
        bridge.add_entity_with_binding(ttl_entity, binding_config)
        definition = bridge.build()
"""

import warnings
import base64
import json
import uuid
import time
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum


logger = logging.getLogger(__name__)


class BindingType(Enum):
    """Type of data binding."""
    NON_TIME_SERIES = "NonTimeSeries"
    TIME_SERIES = "TimeSeries"


class SourceType(Enum):
    """Type of data source."""
    LAKEHOUSE_TABLE = "LakehouseTable"
    KUSTO_TABLE = "KustoTable"


@dataclass
class PropertyBinding:
    """Maps a source column to an entity property."""
    source_column: str
    target_property_id: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sourceColumnName": self.source_column,
            "targetPropertyId": self.target_property_id,
        }


@dataclass
class KeyRefBinding:
    """Maps a source column to an entity key for relationship contextualization."""
    source_column: str
    target_property_id: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sourceColumnName": self.source_column,
            "targetPropertyId": self.target_property_id,
        }


@dataclass
class DataBinding:
    """Complete data binding configuration for an entity."""
    binding_id: str
    entity_type_id: str
    binding_type: BindingType
    source_type: SourceType
    workspace_id: str
    item_id: str  # Lakehouse or Eventhouse ID
    table_name: str
    key_column: str
    timestamp_column: Optional[str] = None  # Required for TimeSeries
    database_name: Optional[str] = None  # Required for Kusto
    cluster_uri: Optional[str] = None  # Required for Kusto in current API
    property_bindings: List[PropertyBinding] = field(default_factory=list)

    @staticmethod
    def generate_id() -> str:
        """Generate a new binding ID."""
        return str(uuid.uuid4())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to API format.
        
        API expects:
        {
            "id": "uuid",
            "dataBindingConfiguration": {
                "dataBindingType": "NonTimeSeries" | "TimeSeries",
                "keySourceColumnName": "...",
                "propertyBindings": [...],
                "sourceTableProperties": {...},
                "timestampColumnName": "..." (for TimeSeries only)
            }
        }
        """
        config = {
            "dataBindingType": self.binding_type.value,
            "keySourceColumnName": self.key_column,
            "propertyBindings": [pb.to_dict() for pb in self.property_bindings],
            "sourceTableProperties": {
                "sourceType": self.source_type.value,
                "workspaceId": self.workspace_id,
                "itemId": self.item_id,
                "sourceTableName": self.table_name,  # API expects sourceTableName, not tableName
            },
        }

        if self.binding_type == BindingType.TIME_SERIES:
            config["timestampColumnName"] = self.timestamp_column

        if self.source_type == SourceType.KUSTO_TABLE and self.database_name:
            config["sourceTableProperties"]["databaseName"] = self.database_name
        if self.source_type == SourceType.KUSTO_TABLE and self.cluster_uri:
            config["sourceTableProperties"]["clusterUri"] = self.cluster_uri

        return {
            "id": self.binding_id,
            "dataBindingConfiguration": config,
        }


@dataclass
class RelationshipContextualization:
    """
    Contextualization binding for relationships between entities.
    
    This binds a relationship type to a fact/bridge table that contains
    foreign keys linking source and target entities.
    
    Example: 
        - Relationship: "produces" (Facility → ProductionBatch)
        - Table: DimProductionBatch
        - Source key: FacilityId (links to Facility entity)
        - Target key: BatchId (links to ProductionBatch entity)
    """
    contextualization_id: str
    relationship_type_id: str
    workspace_id: str
    item_id: str  # Lakehouse or Eventhouse ID
    source_type: SourceType
    table_name: str
    source_schema: Optional[str] = None  # None for lakehouses without schemas enabled
    source_key_column: str = ""  # Column linking to source entity
    source_key_property_id: str = ""  # Property ID of source entity key
    target_key_column: str = ""  # Column linking to target entity
    target_key_property_id: str = ""  # Property ID of target entity key
    database_name: Optional[str] = None  # For Kusto tables
    
    @staticmethod
    def generate_id() -> str:
        """Generate a new contextualization ID."""
        return str(uuid.uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to API format for Contextualization.
        
        Schema based on Fabric Ontology API:
        {
            "id": "uuid",
            "dataBindingTable": {
                "workspaceId": "guid",
                "itemId": "guid",
                "sourceTableName": "TableName",
                "sourceSchema": null,  // null for lakehouses without schemas
                "sourceType": "LakehouseTable"
            },
            "sourceKeyRefBindings": [
                {"sourceColumnName": "FacilityId", "targetPropertyId": "123"}
            ],
            "targetKeyRefBindings": [
                {"sourceColumnName": "BatchId", "targetPropertyId": "456"}
            ]
        }
        """
        result = {
            "id": self.contextualization_id,
            "dataBindingTable": {
                "workspaceId": self.workspace_id,
                "itemId": self.item_id,
                "sourceTableName": self.table_name,
                "sourceSchema": self.source_schema,  # None for lakehouses without schemas
                "sourceType": self.source_type.value,
            },
            "sourceKeyRefBindings": [
                {
                    "sourceColumnName": self.source_key_column,
                    "targetPropertyId": self.source_key_property_id,
                }
            ],
            "targetKeyRefBindings": [
                {
                    "sourceColumnName": self.target_key_column,
                    "targetPropertyId": self.target_key_property_id,
                }
            ],
        }
        
        if self.source_type == SourceType.KUSTO_TABLE and self.database_name:
            result["dataBindingTable"]["databaseName"] = self.database_name
        
        return result


@dataclass
class ParsedRelationshipBinding:
    """Parsed relationship binding from markdown or config."""
    relationship_name: str
    relationship_id: Optional[str] = None
    source_entity: str = ""
    target_entity: str = ""
    table_name: str = ""
    source_key_column: str = ""  # Column linking to source entity
    target_key_column: str = ""  # Column linking to target entity
    source_type: str = "lakehouse"  # "lakehouse" or "eventhouse"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "relationship_name": self.relationship_name,
            "relationship_id": self.relationship_id,
            "source_entity": self.source_entity,
            "target_entity": self.target_entity,
            "table_name": self.table_name,
            "source_key_column": self.source_key_column,
            "target_key_column": self.target_key_column,
            "source_type": self.source_type,
        }


class OntologyBindingBuilder:
    """
    Builder for constructing ontology binding configurations.

    Ontology bindings are configured via the updateDefinition API,
    where DataBinding parts are added to entity type definitions
    and Contextualization parts are added to relationship type definitions.
    
    Supports:
    - Entity data bindings (NonTimeSeries from Lakehouse, TimeSeries from Eventhouse)
    - Relationship contextualizations (foreign key joins between entities)
    
    .. deprecated:: 0.2.0
        Use ``SDKBindingBridge`` from ``demo_automation.binding.sdk_binding_bridge``
        for new implementations. SDKBindingBridge uses the Fabric Ontology SDK
        and provides better validation and API compliance.
    """

    def __init__(
        self,
        workspace_id: str,
        ontology_id: str,
    ):
        """
        Initialize the binding builder.

        Args:
            workspace_id: Fabric workspace ID
            ontology_id: Target ontology ID
            
        .. deprecated:: 0.2.0
            Use ``SDKBindingBridge`` instead.
        """
        warnings.warn(
            "OntologyBindingBuilder is deprecated. Use SDKBindingBridge from "
            "demo_automation.binding.sdk_binding_bridge instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.workspace_id = workspace_id
        self.ontology_id = ontology_id
        # Support multiple bindings per entity: entity_id -> list of bindings
        # An entity can have ONE static binding + MULTIPLE time series bindings
        self._bindings: Dict[str, List[DataBinding]] = {}  # entity_id -> [bindings]
        self._contextualizations: Dict[str, RelationshipContextualization] = {}  # relationship_id -> contextualization
        self._entity_definitions: Dict[str, Dict[str, Any]] = {}
        self._entity_key_properties: Dict[str, str] = {}  # entity_name -> key_property_id

    def add_lakehouse_binding(
        self,
        entity_type_id: str,
        lakehouse_id: str,
        table_name: str,
        key_column: str,
        property_mappings: Dict[str, str],
        binding_id: Optional[str] = None,
    ) -> "OntologyBindingBuilder":
        """
        Add a Lakehouse (NonTimeSeries) binding for an entity.

        Args:
            entity_type_id: ID of the entity type to bind
            lakehouse_id: Lakehouse item ID
            table_name: Name of the table in the lakehouse
            key_column: Column to use as entity key
            property_mappings: Map of source_column -> target_property_id
            binding_id: Optional specific binding ID

        Returns:
            Self for chaining
        """
        binding = DataBinding(
            binding_id=binding_id or DataBinding.generate_id(),
            entity_type_id=entity_type_id,
            binding_type=BindingType.NON_TIME_SERIES,
            source_type=SourceType.LAKEHOUSE_TABLE,
            workspace_id=self.workspace_id,
            item_id=lakehouse_id,
            table_name=table_name,
            key_column=key_column,
            property_bindings=[
                PropertyBinding(source_column=col, target_property_id=prop_id)
                for col, prop_id in property_mappings.items()
            ],
        )

        # Add to list of bindings for this entity (supports multiple bindings)
        if entity_type_id not in self._bindings:
            self._bindings[entity_type_id] = []
        self._bindings[entity_type_id].append(binding)
        logger.debug(f"Added Lakehouse binding for entity {entity_type_id}: {table_name}")
        return self

    def add_eventhouse_binding(
        self,
        entity_type_id: str,
        eventhouse_id: str,
        database_name: str,
        table_name: str,
        key_column: str,
        timestamp_column: str,
        property_mappings: Dict[str, str],
        binding_id: Optional[str] = None,
        cluster_uri: Optional[str] = None,
    ) -> "OntologyBindingBuilder":
        """
        Add an Eventhouse (TimeSeries) binding for an entity.

        Args:
            entity_type_id: ID of the entity type to bind
            eventhouse_id: Eventhouse item ID
            database_name: KQL database name
            table_name: Name of the KQL table
            key_column: Column to use as entity key
            timestamp_column: Column containing timestamps
            property_mappings: Map of source_column -> target_property_id
            binding_id: Optional specific binding ID
            cluster_uri: Eventhouse cluster URI for query execution

        Returns:
            Self for chaining
        """
        binding = DataBinding(
            binding_id=binding_id or DataBinding.generate_id(),
            entity_type_id=entity_type_id,
            binding_type=BindingType.TIME_SERIES,
            source_type=SourceType.KUSTO_TABLE,
            workspace_id=self.workspace_id,
            item_id=eventhouse_id,
            database_name=database_name,
            cluster_uri=cluster_uri,
            table_name=table_name,
            key_column=key_column,
            timestamp_column=timestamp_column,
            property_bindings=[
                PropertyBinding(source_column=col, target_property_id=prop_id)
                for col, prop_id in property_mappings.items()
            ],
        )

        # Add to list of bindings for this entity (supports multiple bindings)
        if entity_type_id not in self._bindings:
            self._bindings[entity_type_id] = []
        self._bindings[entity_type_id].append(binding)
        logger.debug(f"Added Eventhouse binding for entity {entity_type_id}: {table_name}")
        return self

    def register_entity_key_property(
        self,
        entity_name: str,
        key_property_id: str,
    ) -> "OntologyBindingBuilder":
        """
        Register an entity's key property ID for use in relationship contextualizations.
        
        This is needed to map relationship foreign keys to entity key properties.
        
        Args:
            entity_name: Name of the entity (e.g., "Facility", "ProductionBatch")
            key_property_id: The property ID of the entity's key column
            
        Returns:
            Self for chaining
        """
        self._entity_key_properties[entity_name] = key_property_id
        logger.debug(f"Registered key property for {entity_name}: {key_property_id}")
        return self

    def add_relationship_contextualization(
        self,
        relationship_type_id: str,
        lakehouse_id: str,
        table_name: str,
        source_key_column: str,
        source_key_property_id: str,
        target_key_column: str,
        target_key_property_id: str,
        source_schema: Optional[str] = None,
        contextualization_id: Optional[str] = None,
    ) -> "OntologyBindingBuilder":
        """
        Add a Lakehouse-based relationship contextualization.
        
        Contextualizations bind relationships to fact/bridge tables that contain
        foreign keys linking source and target entities.
        
        Args:
            relationship_type_id: ID of the relationship type to bind
            lakehouse_id: Lakehouse item ID containing the bridge table
            table_name: Name of the table containing the relationship data
            source_key_column: Column name that links to source entity
            source_key_property_id: Property ID of the source entity's key
            target_key_column: Column name that links to target entity
            target_key_property_id: Property ID of the target entity's key
            source_schema: Database schema (default: None for lakehouses without schemas)
            contextualization_id: Optional specific contextualization ID
            
        Returns:
            Self for chaining
            
        Example:
            # For relationship "produces" (Facility → ProductionBatch)
            # Table: DimProductionBatch with FacilityId and BatchId columns
            builder.add_relationship_contextualization(
                relationship_type_id="produces",
                lakehouse_id="lakehouse-guid",
                table_name="DimProductionBatch",
                source_key_column="FacilityId",
                source_key_property_id="facility-key-prop-id",
                target_key_column="BatchId",
                target_key_property_id="batch-key-prop-id",
            )
        """
        contextualization = RelationshipContextualization(
            contextualization_id=contextualization_id or RelationshipContextualization.generate_id(),
            relationship_type_id=relationship_type_id,
            workspace_id=self.workspace_id,
            item_id=lakehouse_id,
            source_type=SourceType.LAKEHOUSE_TABLE,
            table_name=table_name,
            source_schema=source_schema,
            source_key_column=source_key_column,
            source_key_property_id=source_key_property_id,
            target_key_column=target_key_column,
            target_key_property_id=target_key_property_id,
        )
        
        self._contextualizations[relationship_type_id] = contextualization
        logger.debug(f"Added Lakehouse contextualization for relationship {relationship_type_id}: {table_name}")
        return self

    def add_eventhouse_relationship_contextualization(
        self,
        relationship_type_id: str,
        eventhouse_id: str,
        database_name: str,
        table_name: str,
        source_key_column: str,
        source_key_property_id: str,
        target_key_column: str,
        target_key_property_id: str,
        source_schema: Optional[str] = None,
        contextualization_id: Optional[str] = None,
    ) -> "OntologyBindingBuilder":
        """
        Add an Eventhouse/KQL-based relationship contextualization.
        
        Similar to Lakehouse contextualization but for KQL tables.
        
        Args:
            relationship_type_id: ID of the relationship type to bind
            eventhouse_id: Eventhouse item ID
            database_name: KQL database name
            table_name: Name of the KQL table containing relationship data
            source_key_column: Column name that links to source entity
            source_key_property_id: Property ID of the source entity's key
            target_key_column: Column name that links to target entity
            target_key_property_id: Property ID of the target entity's key
            source_schema: Database schema (default: None)
            contextualization_id: Optional specific contextualization ID
            
        Returns:
            Self for chaining
        """
        contextualization = RelationshipContextualization(
            contextualization_id=contextualization_id or RelationshipContextualization.generate_id(),
            relationship_type_id=relationship_type_id,
            workspace_id=self.workspace_id,
            item_id=eventhouse_id,
            source_type=SourceType.KUSTO_TABLE,
            table_name=table_name,
            source_schema=source_schema,
            source_key_column=source_key_column,
            source_key_property_id=source_key_property_id,
            target_key_column=target_key_column,
            target_key_property_id=target_key_property_id,
            database_name=database_name,
        )
        
        self._contextualizations[relationship_type_id] = contextualization
        logger.debug(f"Added Eventhouse contextualization for relationship {relationship_type_id}: {table_name}")
        return self

    def add_contextualization_from_parsed(
        self,
        parsed: ParsedRelationshipBinding,
        lakehouse_id: Optional[str] = None,
        eventhouse_id: Optional[str] = None,
        database_name: Optional[str] = None,
        relationship_type_id: Optional[str] = None,
    ) -> "OntologyBindingBuilder":
        """
        Add a contextualization from a parsed relationship binding.
        
        Uses registered entity key properties to resolve property IDs.
        
        Args:
            parsed: Parsed relationship binding from markdown/config
            lakehouse_id: Lakehouse ID (for lakehouse source)
            eventhouse_id: Eventhouse ID (for eventhouse source)
            database_name: KQL database name (for eventhouse source)
            relationship_type_id: Override relationship ID (defaults to parsed name)
            
        Returns:
            Self for chaining
            
        Raises:
            ValueError: If entity key properties are not registered
        """
        rel_id = relationship_type_id or parsed.relationship_id or parsed.relationship_name
        
        # Resolve source entity key property ID
        source_key_prop_id = self._entity_key_properties.get(parsed.source_entity)
        if not source_key_prop_id:
            source_key_prop_id = self.generate_property_id()
            logger.warning(
                f"No key property registered for {parsed.source_entity}, "
                f"using generated ID: {source_key_prop_id}"
            )
        
        # Resolve target entity key property ID
        target_key_prop_id = self._entity_key_properties.get(parsed.target_entity)
        if not target_key_prop_id:
            target_key_prop_id = self.generate_property_id()
            logger.warning(
                f"No key property registered for {parsed.target_entity}, "
                f"using generated ID: {target_key_prop_id}"
            )
        
        if parsed.source_type == "eventhouse" and eventhouse_id and database_name:
            return self.add_eventhouse_relationship_contextualization(
                relationship_type_id=rel_id,
                eventhouse_id=eventhouse_id,
                database_name=database_name,
                table_name=parsed.table_name,
                source_key_column=parsed.source_key_column,
                source_key_property_id=source_key_prop_id,
                target_key_column=parsed.target_key_column,
                target_key_property_id=target_key_prop_id,
            )
        elif lakehouse_id:
            return self.add_relationship_contextualization(
                relationship_type_id=rel_id,
                lakehouse_id=lakehouse_id,
                table_name=parsed.table_name,
                source_key_column=parsed.source_key_column,
                source_key_property_id=source_key_prop_id,
                target_key_column=parsed.target_key_column,
                target_key_property_id=target_key_prop_id,
            )
        else:
            raise ValueError(
                f"Either lakehouse_id or eventhouse_id+database_name required "
                f"for relationship {parsed.relationship_name}"
            )

    def build_definition_parts(
        self,
        existing_definition: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Build the definition parts with binding and contextualization configurations.

        This merges binding parts with existing ontology definition parts,
        including both entity data bindings and relationship contextualizations.
        
        IMPORTANT: This also updates entity definitions to add entityIdParts
        if they're missing, based on the key_column from bindings.

        Args:
            existing_definition: Existing ontology definition to merge with

        Returns:
            List of definition parts ready for updateDefinition API
        """
        parts = []
        has_definition_json = False
        filtered_out_bindings = 0
        filtered_out_contextualizations = 0
        
        # Build mapping of entity_id -> key_property_id from bindings
        # Use the first static (NonTimeSeries) binding's key column
        entity_key_property_ids = {}
        for entity_id, bindings_list in self._bindings.items():
            # Find the first NonTimeSeries binding (static) which has the key
            for binding in bindings_list:
                if binding.binding_type == BindingType.NON_TIME_SERIES:
                    # Find the property ID that matches the key_column
                    for prop_binding in binding.property_bindings:
                        if prop_binding.source_column == binding.key_column:
                            entity_key_property_ids[entity_id] = prop_binding.target_property_id
                            logger.debug(f"Entity {entity_id} key property: {binding.key_column} -> {prop_binding.target_property_id}")
                            break
                    break  # Only need first static binding for key

        # Start with existing parts (if any)
        if existing_definition:
            # Handle both {"definition": {"parts": [...]}} and {"parts": [...]} structures
            existing_parts = existing_definition.get("definition", {}).get("parts", [])
            if not existing_parts:
                existing_parts = existing_definition.get("parts", [])
            
            logger.info(f"Found {len(existing_parts)} existing parts to merge")
            
            # Log all existing parts for debugging
            for p in existing_parts:
                path = p.get("path", "")
                logger.debug(f"Existing part: {path}")
            
            # Determine which entity IDs and relationship IDs have new bindings/contextualizations
            rebound_entity_ids = set(self._bindings.keys())
            rebound_rel_ids = set(self._contextualizations.keys())
            
            # Determine which binding TYPES are being added per entity
            # so we only filter out bindings of the matching type
            rebound_entity_binding_types: Dict[str, set] = {}
            for eid, bindings_list in self._bindings.items():
                types = set()
                for b in bindings_list:
                    types.add(b.binding_type.value)  # "NonTimeSeries" or "TimeSeries"
                rebound_entity_binding_types[eid] = types
            
            # Filter out old binding and contextualization parts only for entities/relationships
            # that are being re-bound AND only for matching binding types.
            # This preserves static bindings when only timeseries are being updated, and vice versa.
            # Also update entity definitions to add entityIdParts if missing
            for p in existing_parts:
                path = p.get("path", "")
                # Only filter out binding parts for entities being re-bound with the same binding type
                if "/DataBindings/" in path:
                    # Extract entity ID from path like "EntityTypes/1000000000004/DataBindings/..."
                    path_segments = path.split("/")
                    entity_id_in_path = path_segments[1] if len(path_segments) >= 3 else ""
                    if entity_id_in_path in rebound_entity_ids:
                        # Check if the existing binding's type matches what we're adding
                        should_filter = False
                        new_types = rebound_entity_binding_types.get(entity_id_in_path, set())
                        try:
                            existing_payload = json.loads(
                                base64.b64decode(p.get("payload", "")).decode("utf-8")
                            )
                            existing_type = existing_payload.get("dataBindingConfiguration", {}).get("dataBindingType", "")
                            if existing_type in new_types:
                                should_filter = True  # Same type - replace it
                            else:
                                should_filter = False  # Different type - keep it
                        except Exception:
                            should_filter = True  # Can't decode, safer to replace
                        
                        if should_filter:
                            filtered_out_bindings += 1
                            logger.info(f"Filtering out old binding part ({existing_type}): {path}")
                            continue
                        else:
                            logger.debug(f"Keeping existing binding (type={existing_type}, not in {new_types}): {path}")
                    # Keep bindings for entities that are NOT being re-bound
                if "/Contextualizations/" in path:
                    path_segments = path.split("/")
                    rel_id_in_path = path_segments[1] if len(path_segments) >= 3 else ""
                    if rel_id_in_path in rebound_rel_ids:
                        filtered_out_contextualizations += 1
                        logger.info(f"Filtering out old contextualization part: {path}")
                        continue
                # Track if definition.json exists
                if path == "definition.json":
                    has_definition_json = True
                
                # Check if this is an entity type definition that needs entityIdParts
                if "EntityTypes/" in path and path.endswith("/definition.json"):
                    # Extract entity ID from path like "EntityTypes/1000000000001/definition.json"
                    path_parts = path.split("/")
                    if len(path_parts) >= 2:
                        entity_id = path_parts[1]
                        key_prop_id = entity_key_property_ids.get(entity_id)
                        
                        if key_prop_id:
                            # Decode, update, and re-encode the entity definition
                            try:
                                payload_b64 = p.get("payload", "")
                                payload_json = base64.b64decode(payload_b64).decode("utf-8")
                                entity_def = json.loads(payload_json)
                                
                                # Check if entityIdParts is missing or empty
                                existing_parts_list = entity_def.get("entityIdParts", [])
                                if not existing_parts_list:
                                    entity_def["entityIdParts"] = [key_prop_id]
                                    logger.info(f"Added entityIdParts [{key_prop_id}] to entity {entity_id} ({entity_def.get('name', 'unknown')})")
                                    
                                    # Re-encode the updated definition
                                    updated_payload = base64.b64encode(
                                        json.dumps(entity_def).encode("utf-8")
                                    ).decode("utf-8")
                                    p = {
                                        "path": path,
                                        "payload": updated_payload,
                                        "payloadType": "InlineBase64",
                                    }
                            except Exception as e:
                                logger.warning(f"Failed to update entity definition for {entity_id}: {e}")
                
                parts.append(p)
            
            logger.info(f"Filtered out {filtered_out_bindings} old bindings, {filtered_out_contextualizations} old contextualizations")
            logger.info(f"Keeping {len(parts)} parts after filtering bindings/contextualizations")
        
        # CRITICAL: definition.json is REQUIRED by the updateDefinition API
        # If it wasn't in existing parts, add an empty one
        if not has_definition_json:
            logger.debug("Adding required definition.json part")
            parts.insert(0, {
                "path": "definition.json",
                "payload": base64.b64encode(b"{}").decode("utf-8"),  # e30=
                "payloadType": "InlineBase64",
            })

        # Add binding parts for each entity (now supports multiple bindings per entity)
        for entity_id, bindings_list in self._bindings.items():
            for binding in bindings_list:
                binding_part = {
                    "path": f"EntityTypes/{entity_id}/DataBindings/{binding.binding_id}.json",
                    "payload": base64.b64encode(
                        json.dumps(binding.to_dict()).encode("utf-8")
                    ).decode("utf-8"),
                    "payloadType": "InlineBase64",
                }
                parts.append(binding_part)
                logger.debug(f"Added binding part for entity {entity_id}: {binding.binding_id} ({binding.binding_type.value})")

        # Add contextualization parts for each relationship
        for rel_id, contextualization in self._contextualizations.items():
            ctx_part = {
                "path": f"RelationshipTypes/{rel_id}/Contextualizations/{contextualization.contextualization_id}.json",
                "payload": base64.b64encode(
                    json.dumps(contextualization.to_dict()).encode("utf-8")
                ).decode("utf-8"),
                "payloadType": "InlineBase64",
            }
            parts.append(ctx_part)
            logger.debug(f"Added contextualization part for relationship {rel_id}")

        return parts

    def build_update_request(
        self,
        existing_definition: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Build the complete updateDefinition request body.

        Args:
            existing_definition: Existing ontology definition

        Returns:
            Request body for updateDefinition API
        """
        return {
            "definition": {
                "parts": self.build_definition_parts(existing_definition),
            }
        }

    @staticmethod
    def generate_property_id() -> str:
        """Generate a 64-bit integer ID for properties (as string)."""
        # Use timestamp-based ID generation
        return str(int(time.time() * 1000000))

    def get_bindings(self) -> Dict[str, List[DataBinding]]:
        """Get all configured bindings (list per entity for multi-binding support)."""
        return self._bindings.copy()

    def get_contextualizations(self) -> Dict[str, RelationshipContextualization]:
        """Get all configured relationship contextualizations."""
        return self._contextualizations.copy()

    def get_entity_key_properties(self) -> Dict[str, str]:
        """Get all registered entity key properties."""
        return self._entity_key_properties.copy()


def build_binding_from_parsed(
    workspace_id: str,
    entity_id: str,
    parsed_binding: Dict[str, Any],
    lakehouse_id: Optional[str] = None,
    eventhouse_id: Optional[str] = None,
    database_name: Optional[str] = None,
) -> DataBinding:
    """
    Create a DataBinding from parsed binding configuration.

    Args:
        workspace_id: Workspace ID
        entity_id: Entity type ID
        parsed_binding: Parsed binding dict from BindingMarkdownParser
        lakehouse_id: Lakehouse ID (for static bindings)
        eventhouse_id: Eventhouse ID (for timeseries bindings)
        database_name: KQL database name (for timeseries bindings)

    Returns:
        DataBinding instance
    """
    binding_type_str = parsed_binding.get("binding_type", "static")
    is_timeseries = binding_type_str == "timeseries"

    if is_timeseries:
        if not eventhouse_id or not database_name:
            raise ValueError("eventhouse_id and database_name required for timeseries binding")

        return DataBinding(
            binding_id=DataBinding.generate_id(),
            entity_type_id=entity_id,
            binding_type=BindingType.TIME_SERIES,
            source_type=SourceType.KUSTO_TABLE,
            workspace_id=workspace_id,
            item_id=eventhouse_id,
            database_name=database_name,
            table_name=parsed_binding.get("table_name", ""),
            key_column=parsed_binding.get("key_column", ""),
            timestamp_column=parsed_binding.get("timestamp_column", ""),
            property_bindings=[
                PropertyBinding(
                    source_column=pm.get("source_column", ""),
                    target_property_id=pm.get("property_id", OntologyBindingBuilder.generate_property_id()),
                )
                for pm in parsed_binding.get("property_mappings", [])
            ],
        )
    else:
        if not lakehouse_id:
            raise ValueError("lakehouse_id required for static binding")

        return DataBinding(
            binding_id=DataBinding.generate_id(),
            entity_type_id=entity_id,
            binding_type=BindingType.NON_TIME_SERIES,
            source_type=SourceType.LAKEHOUSE_TABLE,
            workspace_id=workspace_id,
            item_id=lakehouse_id,
            table_name=parsed_binding.get("table_name", ""),
            cluster_uri=parsed_binding.get("cluster_uri"),
            key_column=parsed_binding.get("key_column", ""),
            property_bindings=[
                PropertyBinding(
                    source_column=pm.get("source_column", ""),
                    target_property_id=pm.get("property_id", OntologyBindingBuilder.generate_property_id()),
                )
                for pm in parsed_binding.get("property_mappings", [])
            ],
        )
