"""
Binding module for Ontology data source bindings.

Handles building and configuring ontology bindings to Lakehouse and Eventhouse data,
including entity data bindings and relationship contextualizations.

NOTE: The SDK Binding Bridge (sdk_binding_bridge.py) is the recommended approach
for new code. It uses the Fabric Ontology SDK builders which provide:
- Official API format compliance
- Built-in validation
- Cleaner code with fluent builders

Legacy OntologyBindingBuilder is still available but deprecated.
"""

# =============================================================================
# SDK Binding Bridge (Recommended)
# =============================================================================
from .sdk_binding_bridge import (
    SDKBindingBridge,
    EntityBindingConfig,
    RelationshipContextConfig,
    TTLEntityInfo,
    TTLRelationshipInfo,
    create_binding_bridge,
    bridge_parsed_entity_to_config,
    bridge_parsed_relationship_to_config,
)

# =============================================================================
# Legacy Builder Classes (Deprecated - use SDK Bridge instead)
# =============================================================================
from .binding_builder import (
    OntologyBindingBuilder,  # Deprecated: Use SDKBindingBridge
    PropertyBinding,
    DataBinding,
    RelationshipContextualization,
    ParsedRelationshipBinding,
    BindingType,
    SourceType,
    build_binding_from_parsed,
)

# =============================================================================
# Binding Parsers (Still used for parsing markdown/YAML binding configs)
# =============================================================================
from .binding_parser import (
    BindingMarkdownParser,
    RelationshipBindingParser,
    ParsedEntityBinding,
    ParsedPropertyMapping,
    parse_demo_bindings,
    parse_relationships_from_binding_file,
)
from .yaml_parser import (
    YamlBindingsParser,
    YamlBindingsConfig,
    EventhouseTableConfig,
    parse_bindings_yaml,
    get_eventhouse_table_configs,
)

__all__ = [
    # ==========================================================================
    # SDK Binding Bridge (Recommended)
    # ==========================================================================
    "SDKBindingBridge",
    "EntityBindingConfig",
    "RelationshipContextConfig",
    "TTLEntityInfo",
    "TTLRelationshipInfo",
    "create_binding_bridge",
    "bridge_parsed_entity_to_config",
    "bridge_parsed_relationship_to_config",
    
    # ==========================================================================
    # Legacy Builder Classes (Deprecated)
    # ==========================================================================
    "OntologyBindingBuilder",  # Deprecated: Use SDKBindingBridge
    "PropertyBinding",
    "DataBinding",
    "RelationshipContextualization",
    "ParsedRelationshipBinding",
    "BindingType",
    "SourceType",
    "build_binding_from_parsed",
    
    # ==========================================================================
    # Parser Classes (Still Active)
    # ==========================================================================
    "BindingMarkdownParser",
    "RelationshipBindingParser",
    "ParsedEntityBinding",
    "ParsedPropertyMapping",
    # YAML Parser classes (v3.2+)
    "YamlBindingsParser",
    "YamlBindingsConfig",
    "EventhouseTableConfig",
    
    # ==========================================================================
    # Functions
    # ==========================================================================
    "parse_demo_bindings",
    "parse_relationships_from_binding_file",
    "parse_bindings_yaml",
    "get_eventhouse_table_configs",
]
