# AddSDK Migration Plan

> **Branch**: https://github.com/falloutxAY/Fabric-Ontology-demoAgent/tree/AddSDK
> **Goal**: Refactor Demo-automation to use the Fabric Ontology SDK for ontology operations
> **SDK Repository**: https://github.com/falloutxAY/Fabric-Ontology-SDK

---

## Progress Tracker

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1 | ✅ Complete | Setup & Dependencies - SDK adapter module |
| Phase 2 | ✅ Complete | Replace Binding Builder - SDK binding bridge |
| Phase 3 | ✅ Complete | Modify Orchestrator - SDK converter and helpers |
| Phase 4 | ⏳ Not Started | Integrate SDK Validation |
| Phase 5 | ⏳ Not Started | Clean Up |

---

## Executive Summary

This plan outlines the migration of `Fabric-Ontology-demoAgent/Demo-automation` to use the `fabric-ontology-sdk` package for all ontology-related operations. The migration will:

1. **Replace** direct API calls for ontology operations with SDK client
2. **Replace** custom binding builders with SDK builders
3. **Replace** custom validation with SDK validation
4. **Keep** TTL parsing, Lakehouse/Eventhouse operations (out of SDK scope)

### Benefits
- Reduced code duplication (~1000 lines removed)
- Shared validation logic across projects
- Official API format compliance guaranteed
- Easier maintenance and updates

---

## Current Architecture Analysis

### Demo-automation Modules to Modify

| Module | Current Responsibility | SDK Replacement |
|--------|----------------------|-----------------|
| `platform/fabric_client.py` | Generic Fabric API + Ontology API | Keep generic, delegate ontology to SDK |
| `binding/binding_builder.py` | OntologyBindingBuilder (818 lines) | Replace with SDK builders |
| `ontology/ttl_converter.py` | TTL → Fabric format (644 lines) | Keep (SDK doesn't parse TTL) |
| `validator.py` | Demo package validation | Augment with SDK validation |

### Code to Remove (~1000 lines)

```
binding/binding_builder.py:
  - DataBinding class (lines 62-110)
  - RelationshipContextualization class (lines 115-200)
  - OntologyBindingBuilder class (lines 225-818)
  
platform/fabric_client.py:
  - update_ontology_definition() method
  - get_ontology_definition() method
```

### Code to Keep

```
binding/binding_parser.py     → Keep (markdown parsing)
binding/yaml_parser.py        → Keep (YAML parsing)
ontology/ttl_converter.py     → Keep (TTL parsing)
platform/lakehouse_client.py  → Keep (data operations)
platform/eventhouse_client.py → Keep (data operations)
platform/onelake_client.py    → Keep (file upload)
orchestrator.py               → Modify (use SDK client)
```

---

## Implementation Plan

### Phase 1: Setup & Dependencies

**Branch**: `AddSDK`

#### Task 1.1: Add SDK Dependency

```diff
# pyproject.toml
dependencies = [
    "azure-identity>=1.15.0",
+   "fabric-ontology-sdk>=0.2.0",
    "requests>=2.31.0",
    ...
]
```

Or install from GitHub:
```toml
dependencies = [
    "fabric-ontology-sdk @ git+https://github.com/falloutxAY/Fabric-Ontology-SDK.git@main",
]
```

#### Task 1.2: Create SDK Adapter Module

Create `demo_automation/sdk_adapter.py`:

```python
"""
Adapter module bridging Demo-automation with Fabric Ontology SDK.

Provides:
- SDK client initialization with Demo-automation auth config
- Conversion helpers between Demo internal formats and SDK formats
"""

from fabric_ontology import OntologyClient, OntologyBuilder
from fabric_ontology.models import PropertyDataType
from fabric_ontology.validation import OntologyValidator

# Type mapping: TTL converter types → SDK types
TTL_TO_SDK_TYPE_MAP = {
    "String": PropertyDataType.STRING,
    "BigInt": PropertyDataType.INT64,
    "Long": PropertyDataType.INT64,
    "Int": PropertyDataType.INT64,
    "Double": PropertyDataType.DOUBLE,
    "Float": PropertyDataType.DOUBLE,
    "Boolean": PropertyDataType.BOOLEAN,
    "DateTime": PropertyDataType.DATETIME,
}

def create_sdk_client(config: "DemoConfiguration") -> OntologyClient:
    """Create SDK client from Demo configuration."""
    from fabric_ontology.auth import FabricAuthenticator
    
    auth = FabricAuthenticator(
        tenant_id=config.fabric.tenant_id,
        use_interactive=config.fabric.use_interactive_auth,
    )
    
    return OntologyClient(
        workspace_id=config.fabric.workspace_id,
        authenticator=auth,
    )
```

---

### Phase 2: Replace Binding Builder

#### Task 2.1: Remove Demo-automation's OntologyBindingBuilder

Delete or deprecate:
- `binding/binding_builder.py` → Lines 62-818

#### Task 2.2: Create SDK Bridge for Bindings

Create `demo_automation/binding/sdk_binding_bridge.py`:

```python
"""
Bridge between Demo parsed bindings and SDK builder.

Converts:
- ParsedEntityBinding → SDK EntityTypeBuilder with bindings
- ParsedRelationshipBinding → SDK RelationshipTypeBuilder with contextualizations
"""

from typing import Dict, List, Optional
from fabric_ontology.builders import OntologyBuilder, EntityTypeBuilder

from .binding_parser import ParsedEntityBinding, ParsedRelationshipBinding
from ..sdk_adapter import TTL_TO_SDK_TYPE_MAP


class SDKBindingBridge:
    """Bridges parsed binding configs to SDK builders."""
    
    def __init__(
        self,
        workspace_id: str,
        lakehouse_id: Optional[str] = None,
        eventhouse_id: Optional[str] = None,
        database_name: Optional[str] = None,
        cluster_uri: Optional[str] = None,
    ):
        self.workspace_id = workspace_id
        self.lakehouse_id = lakehouse_id
        self.eventhouse_id = eventhouse_id
        self.database_name = database_name
        self.cluster_uri = cluster_uri
        self._builder = OntologyBuilder()
    
    def add_entity_from_ttl_and_binding(
        self,
        ttl_entity: "EntityType",  # From ttl_converter
        binding: ParsedEntityBinding,
    ) -> EntityTypeBuilder:
        """
        Add entity type from TTL definition with binding from parsed config.
        
        Merges:
        - TTL: name, properties, key info
        - Binding: table, column mappings
        """
        entity_builder = self._builder.add_entity_type(ttl_entity.name)
        
        # Add properties from TTL
        for prop in ttl_entity.properties:
            sdk_type = TTL_TO_SDK_TYPE_MAP.get(prop.value_type, "String")
            is_key = (prop.name == binding.key_column)
            entity_builder.add_property(prop.name, sdk_type, is_key=is_key)
        
        # Add Lakehouse binding if static
        if binding.binding_type.value == "static" and self.lakehouse_id:
            binding_builder = entity_builder.add_binding()
            binding_builder.lakehouse(
                workspace_id=self.workspace_id,
                lakehouse_id=self.lakehouse_id,
                table_name=binding.table_name,
            )
            for pm in binding.property_mappings:
                binding_builder.map_column(pm.target_property, pm.source_column)
            binding_builder.done()
        
        # Add Eventhouse binding if timeseries
        elif binding.binding_type.value == "timeseries" and self.eventhouse_id:
            binding_builder = entity_builder.add_binding()
            binding_builder.eventhouse(
                workspace_id=self.workspace_id,
                eventhouse_id=self.eventhouse_id,
                database_name=self.database_name,
                table_name=binding.table_name,
                cluster_uri=self.cluster_uri,
                timestamp_column=binding.timestamp_column,
            )
            for pm in binding.property_mappings:
                binding_builder.map_column(pm.target_property, pm.source_column)
            binding_builder.done()
        
        return entity_builder
    
    def add_relationship_contextualization(
        self,
        relationship_name: str,
        source_entity: str,
        target_entity: str,
        parsed: ParsedRelationshipBinding,
    ):
        """Add relationship with contextualization from parsed binding."""
        rel_builder = self._builder.add_relationship_type(
            relationship_name, source_entity, target_entity
        )
        
        if parsed.source_type == "lakehouse" and self.lakehouse_id:
            rel_builder.contextualize_from_lakehouse(
                lakehouse_id=self.lakehouse_id,
                table_name=parsed.table_name,
                source_column=parsed.source_key_column,
                target_column=parsed.target_key_column,
            )
        elif parsed.source_type == "eventhouse" and self.eventhouse_id:
            rel_builder.contextualize_from_eventhouse(
                eventhouse_id=self.eventhouse_id,
                database_name=self.database_name,
                table_name=parsed.table_name,
                source_column=parsed.source_key_column,
                target_column=parsed.target_key_column,
            )
        
        rel_builder.done()
    
    def build(self):
        """Build the complete ontology definition."""
        return self._builder.build()
```

---

### Phase 3: Modify Orchestrator

#### Task 3.1: Update Imports

```diff
# orchestrator.py
- from .binding import (
-     OntologyBindingBuilder,
-     BindingType,
-     parse_demo_bindings,
-     ...
- )
+ from .binding import parse_demo_bindings, parse_bindings_yaml
+ from .binding.sdk_binding_bridge import SDKBindingBridge
+ from .sdk_adapter import create_sdk_client
+ from fabric_ontology import OntologyClient
```

#### Task 3.2: Replace Ontology Creation Flow

Current flow in `orchestrator.py`:
```python
# Current (Lines ~1800-2200)
definition, ontology_name = parse_ttl_file(ttl_path)
ontology = self._fabric_client.create_ontology(ontology_name, definition)
binding_builder = OntologyBindingBuilder(workspace_id, ontology_id)
# ... add bindings ...
parts = binding_builder.build_definition_parts(existing_definition)
self._fabric_client.update_ontology_definition(ontology_id, parts)
```

New flow:
```python
# New flow with SDK
from fabric_ontology import OntologyClient, OntologyBuilder

# 1. Parse TTL (keep existing)
conversion_result = parse_ttl_file(ttl_path)

# 2. Create SDK client
sdk_client = create_sdk_client(self.config)

# 3. Create ontology via SDK
ontology = sdk_client.create_ontology(ontology_name)

# 4. Build definition with SDK builders via bridge
bridge = SDKBindingBridge(
    workspace_id=self.config.fabric.workspace_id,
    lakehouse_id=self.state.lakehouse_id,
    eventhouse_id=self.state.eventhouse_id,
    database_name=self.state.kql_database_name,
    cluster_uri=eventhouse_cluster_uri,
)

# Add entities from TTL + bindings
for ttl_entity in conversion_result.entity_types:
    entity_binding = find_binding_for_entity(ttl_entity.name)
    bridge.add_entity_from_ttl_and_binding(ttl_entity, entity_binding)

# Add relationships from TTL + contextualizations
for ttl_rel in conversion_result.relationship_types:
    rel_binding = find_contextualization_for_relationship(ttl_rel.name)
    bridge.add_relationship_contextualization(
        ttl_rel.name,
        ttl_rel.source.entity_type_id,
        ttl_rel.target.entity_type_id,
        rel_binding,
    )

# 5. Build and update via SDK
definition = bridge.build()
sdk_client.update_definition(ontology.id, definition)
```

#### Task 3.3: Create Conversion Helper

The TTL converter produces its own entity/relationship types. We need to convert to SDK types:

```python
# demo_automation/ontology/sdk_converter.py
"""Convert TTL converter output to SDK builder calls."""

from fabric_ontology.builders import OntologyBuilder
from fabric_ontology.models import PropertyDataType

from .ttl_converter import ConversionResult, EntityType, RelationshipType


def ttl_to_sdk_builder(
    conversion_result: ConversionResult,
) -> OntologyBuilder:
    """
    Convert TTL conversion result to SDK OntologyBuilder.
    
    Note: This creates entity/relationship types WITHOUT bindings.
    Bindings should be added separately via the binding bridge.
    """
    builder = OntologyBuilder()
    
    # Map TTL entity IDs to names for relationship resolution
    entity_id_to_name = {e.id: e.name for e in conversion_result.entity_types}
    
    # Add entity types
    for ttl_entity in conversion_result.entity_types:
        entity_builder = builder.add_entity_type(ttl_entity.name)
        
        for prop in ttl_entity.properties:
            sdk_type = _map_type(prop.value_type)
            # Mark as key if matches TTL key_property_name
            is_key = (
                ttl_entity.key_property_name and 
                prop.name.lower() == ttl_entity.key_property_name.lower()
            )
            entity_builder.add_property(prop.name, sdk_type, is_key=is_key)
        
        entity_builder.done()
    
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
    
    return builder


def _map_type(ttl_type: str) -> str:
    """Map TTL converter type to SDK PropertyDataType."""
    mapping = {
        "String": "String",
        "BigInt": "Int64",
        "Long": "Int64",
        "Int": "Int64",
        "Double": "Double",
        "Float": "Double",
        "Boolean": "Boolean",
        "DateTime": "DateTime",
        "Decimal": "Double",  # SDK rejects Decimal, convert to Double
    }
    return mapping.get(ttl_type, "String")
```

---

### Phase 4: Integrate SDK Validation

#### Task 4.1: Add SDK Validation to Demo Validator

```diff
# validator.py

+ from fabric_ontology.validation import (
+     validate_name,
+     validate_data_type,
+     GQL_RESERVED_WORDS,
+     RECOMMENDED_NAME_LENGTH,
+ )

class DemoPackageValidator:
    def _validate_entity_names(self, entities):
        for entity in entities:
-           # Custom validation logic
-           if entity.name.lower() in GQL_RESERVED_WORDS:
-               self.result.add_error(...)
+           # Use SDK validation
+           try:
+               validate_name(entity.name, "entityType")
+           except ValidationError as e:
+               self.result.add_error(str(e))
```

#### Task 4.2: Add SDK Pre-flight Validation

Before creating ontology:
```python
# orchestrator.py

from fabric_ontology.validation import OntologyValidator

def _create_ontology_step(self):
    # ... build definition ...
    
    # SDK validation before API call
    validator = OntologyValidator(strict=True)
    try:
        validator.validate(definition)
    except ValidationError as e:
        logger.error(f"Ontology validation failed: {e}")
        raise DemoAutomationError(f"Invalid ontology: {e}")
    
    # Proceed with API call
    sdk_client.update_definition(ontology_id, definition)
```

---

### Phase 5: Clean Up

#### Task 5.1: Remove Deprecated Code

| File | Action |
|------|--------|
| `binding/binding_builder.py` | Remove or mark deprecated |
| Custom validation functions duplicated from SDK | Remove |
| Direct ontology API calls in `fabric_client.py` | Remove |

#### Task 5.2: Update Tests

```python
# tests/test_sdk_integration.py

import pytest
from demo_automation.binding.sdk_binding_bridge import SDKBindingBridge
from demo_automation.ontology.sdk_converter import ttl_to_sdk_builder

class TestSDKIntegration:
    def test_ttl_to_sdk_conversion(self):
        """Test TTL conversion result converts to SDK builder."""
        ...
    
    def test_binding_bridge_lakehouse(self):
        """Test binding bridge produces valid SDK bindings."""
        ...
    
    def test_binding_bridge_eventhouse(self):
        """Test binding bridge produces valid SDK eventhouse bindings."""
        ...
```

---

## File Change Summary

### Files to Create

| File | Purpose |
|------|---------|
| `sdk_adapter.py` | SDK client factory, type mappings |
| `binding/sdk_binding_bridge.py` | Parse bindings → SDK builders |
| `ontology/sdk_converter.py` | TTL result → SDK builder |
| `tests/test_sdk_integration.py` | Integration tests |

### Files to Modify

| File | Changes |
|------|---------|
| `pyproject.toml` | Add `fabric-ontology-sdk` dependency |
| `orchestrator.py` | Use SDK client for ontology operations |
| `validator.py` | Use SDK validation functions |
| `platform/fabric_client.py` | Remove ontology-specific methods |
| `binding/__init__.py` | Update exports |

### Files to Remove/Deprecate

| File | Lines Removed |
|------|---------------|
| `binding/binding_builder.py` | ~750 lines (keep ParsedRelationshipBinding) |

---

## Migration Checklist

```
Phase 1: Setup
[ ] Add fabric-ontology-sdk to pyproject.toml
[ ] Create sdk_adapter.py
[ ] Verify SDK import works

Phase 2: Binding Builder
[ ] Create sdk_binding_bridge.py
[ ] Test binding bridge with sample data
[ ] Remove/deprecate OntologyBindingBuilder

Phase 3: Orchestrator
[ ] Create ontology/sdk_converter.py
[ ] Update orchestrator imports
[ ] Replace ontology creation flow
[ ] Replace binding configuration flow
[ ] Test end-to-end demo setup

Phase 4: Validation
[ ] Integrate SDK validation in validator.py
[ ] Add pre-flight validation in orchestrator
[ ] Test validation catches expected errors

Phase 5: Clean Up
[ ] Remove deprecated binding_builder.py code
[ ] Remove duplicate validation code
[ ] Update fabric_client.py (remove ontology methods)
[ ] Update all tests
[ ] Update README.md

Final Verification
[ ] Run full demo setup with SDK
[ ] Verify ontology created correctly in Fabric
[ ] Verify bindings work (data flows)
[ ] All tests pass
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| SDK API changes | Pin SDK version in dependencies |
| TTL → SDK type mismatch | Create comprehensive type mapping tests |
| Missing SDK features | Keep fallback to direct API if needed |
| Performance regression | Profile SDK vs direct calls |

---

## Timeline Estimate

| Phase | Effort |
|-------|--------|
| Phase 1: Setup | 1 hour |
| Phase 2: Binding Builder | 2-3 hours |
| Phase 3: Orchestrator | 3-4 hours |
| Phase 4: Validation | 1-2 hours |
| Phase 5: Clean Up | 1-2 hours |
| **Total** | **8-12 hours** |

---

## References

- SDK Repository: https://github.com/falloutxAY/Fabric-Ontology-SDK
- SDK Porting Guide: [SDK-PORTING-GUIDE.md](../SDK-PORTING-GUIDE.md)
- Official API Docs: https://learn.microsoft.com/en-us/rest/api/fabric/ontology/items
