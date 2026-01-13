"""
TTL to Microsoft Fabric Ontology Converter.

This module provides functionality to parse RDF TTL files and convert them
to Microsoft Fabric Ontology API format. It implements the conversion logic
based on the rdf-dtdl-fabric-ontology-converter patterns.

Usage:
    from demo_automation.ontology import parse_ttl_file
    
    definition, ontology_name = parse_ttl_file("path/to/ontology.ttl")
"""

import base64
import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Try to import rdflib for TTL parsing
try:
    from rdflib import Graph, Namespace, RDF, RDFS, OWL, XSD, URIRef
    from rdflib.term import Literal as RDFLiteral
    RDFLIB_AVAILABLE = True
except ImportError:
    RDFLIB_AVAILABLE = False
    logger.warning("rdflib not installed. TTL parsing will not be available.")


# XSD to Fabric type mapping
XSD_TO_FABRIC_TYPE: Dict[str, str] = {
    "string": "String",
    "boolean": "Boolean",
    "dateTime": "DateTime",
    "date": "DateTime",
    "time": "DateTime",
    "integer": "BigInt",
    "int": "Int",
    "long": "Long",
    "short": "Int",
    "byte": "Int",
    "nonNegativeInteger": "BigInt",
    "positiveInteger": "BigInt",
    "negativeInteger": "BigInt",
    "nonPositiveInteger": "BigInt",
    "unsignedLong": "BigInt",
    "unsignedInt": "BigInt",
    "unsignedShort": "Int",
    "unsignedByte": "Int",
    "double": "Double",
    "float": "Float",
    "decimal": "Decimal",
}


@dataclass
class EntityTypeProperty:
    """Represents a property of an entity type."""
    id: str
    name: str
    value_type: str = "String"
    description: str = ""
    is_timeseries: bool = False


@dataclass
class EntityType:
    """Represents an entity type in the ontology."""
    id: str
    name: str
    description: str = ""
    key_property_id: Optional[str] = None  # Will be converted to entityIdParts
    key_property_name: Optional[str] = None  # Key property name from TTL comment
    base_entity_type_id: Optional[str] = None
    properties: List[EntityTypeProperty] = field(default_factory=list)
    timeseries_properties: List[EntityTypeProperty] = field(default_factory=list)


@dataclass
class RelationshipEnd:
    """Represents an end of a relationship."""
    entity_type_id: str
    multiplicity: str = "Many"


@dataclass
class RelationshipType:
    """Represents a relationship type in the ontology."""
    id: str
    name: str
    source: RelationshipEnd
    target: RelationshipEnd
    description: str = ""


@dataclass
class ConversionResult:
    """Result of TTL to Fabric conversion."""
    entity_types: List[EntityType]
    relationship_types: List[RelationshipType]
    warnings: List[str] = field(default_factory=list)
    skipped_items: List[Dict[str, str]] = field(default_factory=list)


class TTLToFabricConverter:
    """
    Converts RDF TTL ontologies to Microsoft Fabric Ontology format.
    
    This converter parses OWL/RDFS ontologies and transforms them into
    the Fabric Ontology API format with entity types, properties, and
    relationship types.
    """
    
    # Base ID prefix for generating unique IDs
    DEFAULT_ID_PREFIX = 1000000000000
    
    def __init__(self, id_prefix: int = DEFAULT_ID_PREFIX):
        """
        Initialize the converter.
        
        Args:
            id_prefix: Base prefix for generating unique IDs
        """
        if not RDFLIB_AVAILABLE:
            raise ImportError(
                "rdflib is required for TTL parsing. "
                "Install it with: pip install rdflib"
            )
        
        self.id_prefix = id_prefix
        self._id_counter = 0
        self._uri_to_id: Dict[str, str] = {}
        self._entity_types: List[EntityType] = []
        self._relationship_types: List[RelationshipType] = []
        self._warnings: List[str] = []
        self._skipped_items: List[Dict[str, str]] = []
    
    def _generate_id(self) -> str:
        """Generate a unique ID for entities and properties."""
        self._id_counter += 1
        return str(self.id_prefix + self._id_counter)
    
    def _uri_to_name(self, uri: URIRef) -> str:
        """Extract a clean name from a URI."""
        uri_str = str(uri)
        
        # Try fragment identifier first
        if "#" in uri_str:
            name = uri_str.split("#")[-1]
        # Then try last path segment
        elif "/" in uri_str:
            name = uri_str.rstrip("/").split("/")[-1]
        else:
            name = uri_str
        
        # Clean up the name for Fabric compliance
        # Fabric names: alphanumeric + underscore, start with letter, max 100 chars
        cleaned = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        if cleaned and not cleaned[0].isalpha():
            cleaned = 'E_' + cleaned
        cleaned = cleaned[:100]
        
        return cleaned or "UnnamedEntity"
    
    def _get_xsd_type(self, range_uri: Optional[URIRef]) -> str:
        """Map XSD type to Fabric type."""
        if not range_uri:
            return "String"
        
        uri_str = str(range_uri)
        
        # Extract type name from XSD namespace
        if "XMLSchema#" in uri_str:
            type_name = uri_str.split("#")[-1]
            return XSD_TO_FABRIC_TYPE.get(type_name, "String")
        
        # Default to String for unknown types
        return "String"
    
    def _reset_state(self) -> None:
        """Reset converter state for a fresh conversion."""
        self._id_counter = 0
        self._uri_to_id = {}
        self._entity_types = []
        self._relationship_types = []
        self._warnings = []
        self._skipped_items = []
    
    def parse_ttl(self, ttl_content: str) -> ConversionResult:
        """
        Parse TTL content and extract entity and relationship types.
        
        Args:
            ttl_content: The TTL content as a string
            
        Returns:
            ConversionResult with entity types, relationship types, and warnings
            
        Raises:
            ValueError: If TTL content is empty or has invalid syntax
        """
        if not ttl_content or not ttl_content.strip():
            raise ValueError("Empty TTL content")
        
        self._reset_state()
        
        # Parse the TTL content
        graph = Graph()
        try:
            graph.parse(data=ttl_content, format="turtle")
        except Exception as e:
            raise ValueError(f"Invalid TTL syntax: {e}")
        
        logger.info(f"Parsed TTL with {len(graph)} triples")
        
        # Step 1: Extract all classes (entity types)
        self._extract_classes(graph)
        
        # Step 2: Extract data properties
        self._extract_data_properties(graph)
        
        # Step 3: Extract object properties (relationships)
        self._extract_object_properties(graph)
        
        logger.info(
            f"Converted: {len(self._entity_types)} entity types, "
            f"{len(self._relationship_types)} relationship types"
        )
        
        return ConversionResult(
            entity_types=self._entity_types.copy(),
            relationship_types=self._relationship_types.copy(),
            warnings=self._warnings.copy(),
            skipped_items=self._skipped_items.copy(),
        )
    
    def _extract_classes(self, graph: Graph) -> None:
        """Extract OWL/RDFS classes as entity types."""
        # Find all classes (owl:Class and rdfs:Class)
        class_uris = set()
        for class_type in [OWL.Class, RDFS.Class]:
            for s in graph.subjects(RDF.type, class_type):
                if isinstance(s, URIRef):
                    class_uris.add(s)
        
        for class_uri in class_uris:
            name = self._uri_to_name(class_uri)
            entity_id = self._generate_id()
            
            # Store URI to ID mapping
            self._uri_to_id[str(class_uri)] = entity_id
            
            # Get label if available
            labels = list(graph.objects(class_uri, RDFS.label))
            if labels:
                name = str(labels[0])
                # Clean for Fabric
                name = re.sub(r'[^a-zA-Z0-9_]', '_', name)[:100]
                if name and not name[0].isalpha():
                    name = 'E_' + name
            
            # Get description from comment and parse key property
            comments = list(graph.objects(class_uri, RDFS.comment))
            description = str(comments[0]) if comments else ""
            
            # Extract key property name from comment like "Key: ProductId (string)"
            key_property_name = None
            if description:
                key_match = re.search(r'Key:\s*(\w+)', description, re.IGNORECASE)
                if key_match:
                    key_property_name = key_match.group(1)
                    logger.debug(f"Found key property name '{key_property_name}' from comment")
            
            # Check for base class (rdfs:subClassOf)
            base_entity_type_id = None
            for base_class in graph.objects(class_uri, RDFS.subClassOf):
                if isinstance(base_class, URIRef):
                    base_uri_str = str(base_class)
                    if base_uri_str in self._uri_to_id:
                        base_entity_type_id = self._uri_to_id[base_uri_str]
                        break
            
            entity_type = EntityType(
                id=entity_id,
                name=name,
                description=description,
                key_property_name=key_property_name,
                base_entity_type_id=base_entity_type_id,
            )
            self._entity_types.append(entity_type)
            logger.debug(f"Extracted entity type: {name} (ID: {entity_id}, key: {key_property_name})")
    
    def _extract_data_properties(self, graph: Graph) -> None:
        """Extract OWL data properties as entity properties."""
        for prop_uri in graph.subjects(RDF.type, OWL.DatatypeProperty):
            if not isinstance(prop_uri, URIRef):
                continue
            
            prop_name = self._uri_to_name(prop_uri)
            prop_id = self._generate_id()
            
            # Get label if available
            labels = list(graph.objects(prop_uri, RDFS.label))
            if labels:
                prop_name = str(labels[0])
                prop_name = re.sub(r'[^a-zA-Z0-9_]', '_', prop_name)[:100]
                if prop_name and not prop_name[0].isalpha():
                    prop_name = 'P_' + prop_name
            
            # Get domain (which entity type this property belongs to)
            domains = list(graph.objects(prop_uri, RDFS.domain))
            
            # Get range (data type)
            ranges = list(graph.objects(prop_uri, RDFS.range))
            value_type = self._get_xsd_type(ranges[0] if ranges else None)
            
            # Check rdfs:comment for "(timeseries)" annotation
            is_timeseries = False
            comments = list(graph.objects(prop_uri, RDFS.comment))
            prop_description = ""
            if comments:
                prop_description = str(comments[0])
                if "(timeseries)" in prop_description.lower():
                    is_timeseries = True
                    logger.debug(f"Property {prop_name} marked as timeseries from rdfs:comment")
            
            # Create property and add to domain entities
            prop = EntityTypeProperty(
                id=prop_id,
                name=prop_name,
                value_type=value_type,
                description=prop_description,
                is_timeseries=is_timeseries,
            )
            
            if domains:
                for domain_uri in domains:
                    if isinstance(domain_uri, URIRef):
                        domain_id = self._uri_to_id.get(str(domain_uri))
                        if domain_id:
                            # Find entity and add property to appropriate list
                            for entity in self._entity_types:
                                if entity.id == domain_id:
                                    if is_timeseries:
                                        entity.timeseries_properties.append(prop)
                                        logger.debug(
                                            f"Added timeseries property {prop_name} to {entity.name}"
                                        )
                                    else:
                                        entity.properties.append(prop)
                                        logger.debug(
                                            f"Added property {prop_name} to {entity.name}"
                                        )
                                    break
            else:
                # No domain specified - skip with warning
                self._warnings.append(
                    f"Property '{prop_name}' has no domain and was skipped"
                )
    
    def _extract_object_properties(self, graph: Graph) -> None:
        """Extract OWL object properties as relationship types."""
        for prop_uri in graph.subjects(RDF.type, OWL.ObjectProperty):
            if not isinstance(prop_uri, URIRef):
                continue
            
            rel_name = self._uri_to_name(prop_uri)
            rel_id = self._generate_id()
            
            # Get label if available
            labels = list(graph.objects(prop_uri, RDFS.label))
            if labels:
                rel_name = str(labels[0])
                rel_name = re.sub(r'[^a-zA-Z0-9_]', '_', rel_name)[:100]
                if rel_name and not rel_name[0].isalpha():
                    rel_name = 'R_' + rel_name
            
            # Get description
            comments = list(graph.objects(prop_uri, RDFS.comment))
            description = str(comments[0]) if comments else ""
            
            # Get domain (source entity)
            domains = list(graph.objects(prop_uri, RDFS.domain))
            # Get range (target entity)
            ranges = list(graph.objects(prop_uri, RDFS.range))
            
            if not domains or not ranges:
                self._warnings.append(
                    f"Relationship '{rel_name}' missing domain or range, skipped"
                )
                continue
            
            # Get first domain and range as URIs
            source_uri = domains[0] if isinstance(domains[0], URIRef) else None
            target_uri = ranges[0] if isinstance(ranges[0], URIRef) else None
            
            if not source_uri or not target_uri:
                self._warnings.append(
                    f"Relationship '{rel_name}' has non-URI domain/range, skipped"
                )
                continue
            
            source_id = self._uri_to_id.get(str(source_uri))
            target_id = self._uri_to_id.get(str(target_uri))
            
            if not source_id or not target_id:
                self._warnings.append(
                    f"Relationship '{rel_name}' references unknown entity types, skipped"
                )
                continue
            
            relationship = RelationshipType(
                id=rel_id,
                name=rel_name,
                source=RelationshipEnd(entity_type_id=source_id),
                target=RelationshipEnd(entity_type_id=target_id),
                description=description,
            )
            self._relationship_types.append(relationship)
            logger.debug(f"Extracted relationship: {rel_name}")


def _encode_payload(data: Dict[str, Any]) -> str:
    """Encode a dictionary as base64 JSON payload."""
    json_str = json.dumps(data, ensure_ascii=False)
    return base64.b64encode(json_str.encode("utf-8")).decode("utf-8")


def convert_to_fabric_definition(
    entity_types: List[EntityType],
    relationship_types: List[RelationshipType],
    ontology_name: str = "ImportedOntology",
) -> Dict[str, Any]:
    """
    Convert entity and relationship types to Fabric Ontology definition format.
    
    The Fabric Ontology API requires a specific structure with:
    1. .platform - Platform metadata with schema info
    2. definition.json - Definition metadata (can be empty)
    3. EntityTypes/{name}/definition.json - Entity type definitions
    4. RelationshipTypes/{name}/definition.json - Relationship type definitions
    
    Each entity type must include:
    - id: Unique numeric string identifier
    - namespace: "usertypes" for custom types
    - name: Entity name (alphanumeric + underscore)
    - displayName: Human-readable name
    - namespaceType: "Custom" for user-defined types
    - visibility: "Visible" or "Hidden"
    - properties: Array of property definitions
    
    Args:
        entity_types: List of entity types
        relationship_types: List of relationship types
        ontology_name: Name for the ontology
        
    Returns:
        Fabric Ontology definition with parts array
    """
    parts = []
    
    # 1. Add .platform metadata (REQUIRED by Fabric API)
    platform_content = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/platformProperties.json",
        "metadata": {
            "type": "Ontology",
            "displayName": ontology_name
        },
        "config": {
            "version": "1.0",
            "type": "Ontology"
        }
    }
    parts.append({
        "path": ".platform",
        "payload": _encode_payload(platform_content),
        "payloadType": "InlineBase64",
    })
    
    # 2. Add definition.json (REQUIRED by Fabric API, can be minimal)
    definition_content = {
        "version": "1.0",
        "formatVersion": "1.0"
    }
    parts.append({
        "path": "definition.json",
        "payload": _encode_payload(definition_content),
        "payloadType": "InlineBase64",
    })
    
    # 3. Add entity types with full Fabric-compliant structure
    for entity in entity_types:
        # Build properties list with required fields (static properties)
        properties = []
        for prop in entity.properties:
            prop_data = {
                "id": prop.id,
                "name": prop.name,
                "displayName": prop.name.replace("_", " "),
                "valueType": prop.value_type,
            }
            if prop.description:
                prop_data["description"] = prop.description
            properties.append(prop_data)
        
        # Build timeseries properties list
        timeseries_properties = []
        for prop in entity.timeseries_properties:
            prop_data = {
                "id": prop.id,
                "name": prop.name,
                "displayName": prop.name.replace("_", " "),
                "valueType": prop.value_type,
            }
            if prop.description:
                prop_data["description"] = prop.description
            timeseries_properties.append(prop_data)
        
        # Build entity payload with all required Fabric fields
        entity_payload = {
            "id": entity.id,
            "namespace": "usertypes",
            "name": entity.name,
            "displayName": entity.name.replace("_", " "),
            "namespaceType": "Custom",
            "visibility": "Visible",
            "properties": properties,
        }
        
        # Add timeseries properties if present
        if timeseries_properties:
            entity_payload["timeseriesProperties"] = timeseries_properties
            logger.debug(f"Entity {entity.name}: {len(properties)} static, {len(timeseries_properties)} timeseries properties")
        
        # Add optional fields if present
        # Resolve key_property_name to key_property_id if needed
        entity_id_parts = []
        if entity.key_property_id:
            entity_id_parts = [entity.key_property_id]
        elif entity.key_property_name:
            # Find the property ID by name
            for prop in entity.properties:
                if prop.name.lower() == entity.key_property_name.lower():
                    entity_id_parts = [prop.id]
                    logger.debug(f"Resolved key property '{entity.key_property_name}' to ID '{prop.id}' for entity '{entity.name}'")
                    break
        # Auto-infer key property if not found - look for *Id pattern
        if not entity_id_parts and properties:
            for prop_data in properties:
                prop_name = prop_data.get("name", "")
                if prop_name.lower().endswith("id") and prop_data.get("valueType") in ("String", "BigInt"):
                    entity_id_parts = [prop_data["id"]]
                    logger.debug(f"Auto-inferred key property '{prop_name}' (ID: {prop_data['id']}) for entity '{entity.name}'")
                    break
        
        if entity_id_parts:
            entity_payload["entityIdParts"] = entity_id_parts
        if entity.base_entity_type_id:
            entity_payload["baseEntityTypeId"] = entity.base_entity_type_id
        if entity.description:
            entity_payload["description"] = entity.description
        
        # Use ID-based path as per Fabric API spec
        parts.append({
            "path": f"EntityTypes/{entity.id}/definition.json",
            "payload": _encode_payload(entity_payload),
            "payloadType": "InlineBase64",
        })
    
    # 4. Add relationship types with full Fabric-compliant structure
    for rel in relationship_types:
        rel_payload = {
            "id": rel.id,
            "namespace": "usertypes",
            "name": rel.name,
            "displayName": rel.name.replace("_", " "),
            "namespaceType": "Custom",
            "visibility": "Visible",
            "source": {
                "entityTypeId": rel.source.entity_type_id,
                "multiplicity": rel.source.multiplicity,
            },
            "target": {
                "entityTypeId": rel.target.entity_type_id,
                "multiplicity": rel.target.multiplicity,
            },
        }
        
        if rel.description:
            rel_payload["description"] = rel.description
        
        # Use ID-based path as per Fabric API spec
        parts.append({
            "path": f"RelationshipTypes/{rel.id}/definition.json",
            "payload": _encode_payload(rel_payload),
            "payloadType": "InlineBase64",
        })
    
    return {"parts": parts}


def parse_ttl_content(
    ttl_content: str,
    id_prefix: int = TTLToFabricConverter.DEFAULT_ID_PREFIX,
) -> Tuple[Dict[str, Any], str]:
    """
    Parse TTL content and return the Fabric Ontology definition.
    
    Args:
        ttl_content: TTL content as string
        id_prefix: Base prefix for generating unique IDs
        
    Returns:
        Tuple of (Fabric Ontology definition dict, extracted ontology name)
        
    Raises:
        ValueError: If content is empty or invalid
    """
    if not RDFLIB_AVAILABLE:
        raise ImportError(
            "rdflib is required for TTL parsing. "
            "Install it with: pip install rdflib"
        )
    
    converter = TTLToFabricConverter(id_prefix=id_prefix)
    result = converter.parse_ttl(ttl_content)
    
    # Try to extract ontology name from the TTL
    graph = Graph()
    graph.parse(data=ttl_content, format="turtle")
    
    ontology_name = "ImportedOntology"
    for s in graph.subjects(RDF.type, OWL.Ontology):
        # Try to get label
        labels = list(graph.objects(s, RDFS.label))
        if labels:
            label = str(labels[0])
            # Clean up for Fabric naming requirements
            ontology_name = re.sub(r'[^a-zA-Z0-9_]', '_', label)
            ontology_name = ontology_name[:100]
            if ontology_name and not ontology_name[0].isalpha():
                ontology_name = 'O_' + ontology_name
        break
    
    definition = convert_to_fabric_definition(
        result.entity_types,
        result.relationship_types,
        ontology_name,
    )
    
    return definition, ontology_name


def parse_ttl_file(
    file_path: str,
    id_prefix: int = TTLToFabricConverter.DEFAULT_ID_PREFIX,
) -> Tuple[Dict[str, Any], str]:
    """
    Parse a TTL file and return the Fabric Ontology definition.
    
    Args:
        file_path: Path to the TTL file
        id_prefix: Base prefix for generating unique IDs
        
    Returns:
        Tuple of (Fabric Ontology definition dict, extracted ontology name)
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        ValueError: If the file content is invalid
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"TTL file not found: {file_path}")
    
    ttl_content = path.read_text(encoding="utf-8")
    return parse_ttl_content(ttl_content, id_prefix)
