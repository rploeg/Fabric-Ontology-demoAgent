"""
Ontology processing module.

Provides TTL to Fabric Ontology conversion functionality.
"""

from .ttl_converter import (
    TTLToFabricConverter,
    parse_ttl_file,
    parse_ttl_content,
)

__all__ = [
    "TTLToFabricConverter",
    "parse_ttl_file",
    "parse_ttl_content",
]
