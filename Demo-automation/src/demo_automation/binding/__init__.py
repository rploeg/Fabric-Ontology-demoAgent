"""
Binding module for Ontology data source bindings.

Handles building and configuring ontology bindings to Lakehouse and Eventhouse data,
including entity data bindings and relationship contextualizations.
"""

from .binding_builder import (
    OntologyBindingBuilder,
    PropertyBinding,
    DataBinding,
    RelationshipContextualization,
    ParsedRelationshipBinding,
    BindingType,
    SourceType,
    build_binding_from_parsed,
)
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
    # Builder classes
    "OntologyBindingBuilder",
    "PropertyBinding",
    "DataBinding",
    "RelationshipContextualization",
    "ParsedRelationshipBinding",
    "BindingType",
    "SourceType",
    "build_binding_from_parsed",
    # Parser classes
    "BindingMarkdownParser",
    "RelationshipBindingParser",
    "ParsedEntityBinding",
    "ParsedPropertyMapping",
    # YAML Parser classes (v3.2+)
    "YamlBindingsParser",
    "YamlBindingsConfig",
    "EventhouseTableConfig",
    # Functions
    "parse_demo_bindings",
    "parse_relationships_from_binding_file",
    "parse_bindings_yaml",
    "get_eventhouse_table_configs",
]
