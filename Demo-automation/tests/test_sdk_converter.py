"""
Tests for SDK Converter Module.

Tests the sdk_converter module which bridges TTL conversion results
to SDK OntologyBuilder and SDKBindingBridge.
"""

import pytest
from unittest.mock import MagicMock, patch

from demo_automation.ontology.sdk_converter import (
    ttl_to_sdk_builder,
    ttl_entity_to_sdk_info,
    ttl_relationship_to_sdk_info,
    ttl_result_to_sdk_infos,
    create_bridge_from_ttl,
)
from demo_automation.ontology.ttl_converter import (
    ConversionResult,
    EntityType,
    RelationshipType,
    EntityTypeProperty,
    RelationshipEnd,
)
from demo_automation.binding.sdk_binding_bridge import TTLEntityInfo, TTLRelationshipInfo


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_entity_type():
    """Sample entity type from TTL conversion."""
    return EntityType(
        id="1000000000001",
        name="Facility",
        description="Manufacturing facility. Key: FacilityId (string)",
        key_property_id="1000000000010",
        key_property_name="FacilityId",
        properties=[
            EntityTypeProperty(id="1000000000010", name="FacilityId", value_type="String"),
            EntityTypeProperty(id="1000000000011", name="FacilityName", value_type="String"),
            EntityTypeProperty(id="1000000000012", name="Capacity", value_type="BigInt"),
            EntityTypeProperty(id="1000000000013", name="IsActive", value_type="Boolean"),
        ],
    )


@pytest.fixture
def sample_entity_type_with_decimal():
    """Entity type with decimal property (should map to Double)."""
    return EntityType(
        id="1000000000002",
        name="ManufacturedProduct",
        key_property_name="ManufacturedProductId",
        properties=[
            EntityTypeProperty(id="1000000000020", name="ManufacturedProductId", value_type="String"),
            EntityTypeProperty(id="1000000000021", name="Price", value_type="Decimal"),
            EntityTypeProperty(id="1000000000022", name="Weight", value_type="Float"),
        ],
    )


@pytest.fixture
def sample_relationship_type():
    """Sample relationship type from TTL conversion."""
    return RelationshipType(
        id="2000000000001",
        name="produces",
        source=RelationshipEnd(entity_type_id="1000000000001", multiplicity="Many"),
        target=RelationshipEnd(entity_type_id="1000000000002", multiplicity="Many"),
        description="Facility produces ManufacturedProducts",
    )


@pytest.fixture
def sample_conversion_result(sample_entity_type, sample_entity_type_with_decimal, sample_relationship_type):
    """Sample conversion result with entities and relationships."""
    return ConversionResult(
        entity_types=[sample_entity_type, sample_entity_type_with_decimal],
        relationship_types=[sample_relationship_type],
        warnings=[],
        skipped_items=[],
    )


@pytest.fixture
def workspace_id():
    """Sample workspace ID."""
    return "12345678-1234-1234-1234-123456789012"


@pytest.fixture
def lakehouse_id():
    """Sample lakehouse ID."""
    return "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


# =============================================================================
# ttl_entity_to_sdk_info Tests
# =============================================================================

class TestTtlEntityToSdkInfo:
    """Tests for ttl_entity_to_sdk_info function."""
    
    def test_basic_conversion(self, sample_entity_type):
        """Test basic entity type conversion."""
        sdk_info = ttl_entity_to_sdk_info(sample_entity_type)
        
        assert isinstance(sdk_info, TTLEntityInfo)
        assert sdk_info.name == "Facility"
        assert sdk_info.key_property_name == "FacilityId"
        assert len(sdk_info.properties) == 4
    
    def test_key_property_marked(self, sample_entity_type):
        """Test that key property is correctly marked."""
        sdk_info = ttl_entity_to_sdk_info(sample_entity_type)
        
        key_props = [p for p in sdk_info.properties if p.get("is_key")]
        assert len(key_props) == 1
        assert key_props[0]["name"] == "FacilityId"
    
    def test_property_types_preserved(self, sample_entity_type):
        """Test that property types are preserved."""
        sdk_info = ttl_entity_to_sdk_info(sample_entity_type)
        
        props_by_name = {p["name"]: p for p in sdk_info.properties}
        assert props_by_name["FacilityId"]["value_type"] == "String"
        assert props_by_name["Capacity"]["value_type"] == "BigInt"
        assert props_by_name["IsActive"]["value_type"] == "Boolean"
    
    def test_entity_without_key(self):
        """Test entity without key property name."""
        entity = EntityType(
            id="1000000000099",
            name="NoKeyEntity",
            properties=[
                EntityTypeProperty(id="100", name="PropA", value_type="String"),
            ],
        )
        
        sdk_info = ttl_entity_to_sdk_info(entity)
        
        assert sdk_info.key_property_name is None
        # No property should be marked as key
        key_props = [p for p in sdk_info.properties if p.get("is_key")]
        assert len(key_props) == 0


# =============================================================================
# ttl_relationship_to_sdk_info Tests
# =============================================================================

class TestTtlRelationshipToSdkInfo:
    """Tests for ttl_relationship_to_sdk_info function."""
    
    def test_basic_conversion(self, sample_relationship_type):
        """Test basic relationship type conversion."""
        entity_id_to_name = {
            "1000000000001": "Facility",
            "1000000000002": "ManufacturedProduct",
        }
        
        sdk_info = ttl_relationship_to_sdk_info(sample_relationship_type, entity_id_to_name)
        
        assert isinstance(sdk_info, TTLRelationshipInfo)
        assert sdk_info.name == "produces"
        assert sdk_info.source_entity_name == "Facility"
        assert sdk_info.target_entity_name == "ManufacturedProduct"
    
    def test_missing_source_entity(self, sample_relationship_type):
        """Test with missing source entity in mapping."""
        entity_id_to_name = {
            "1000000000002": "ManufacturedProduct",
            # Missing source entity
        }
        
        sdk_info = ttl_relationship_to_sdk_info(sample_relationship_type, entity_id_to_name)
        
        assert sdk_info is None
    
    def test_missing_target_entity(self, sample_relationship_type):
        """Test with missing target entity in mapping."""
        entity_id_to_name = {
            "1000000000001": "Facility",
            # Missing target entity
        }
        
        sdk_info = ttl_relationship_to_sdk_info(sample_relationship_type, entity_id_to_name)
        
        assert sdk_info is None


# =============================================================================
# ttl_to_sdk_builder Tests
# =============================================================================

class TestTtlToSdkBuilder:
    """Tests for ttl_to_sdk_builder function."""
    
    def test_builds_entities(self, sample_conversion_result):
        """Test that entities are built correctly."""
        builder = ttl_to_sdk_builder(sample_conversion_result, seed=42)
        definition = builder.build()
        
        assert len(definition.entity_types) == 2
        entity_names = [e.name for e in definition.entity_types]
        assert "Facility" in entity_names
        assert "ManufacturedProduct" in entity_names
    
    def test_builds_relationships(self, sample_conversion_result):
        """Test that relationships are built correctly."""
        builder = ttl_to_sdk_builder(sample_conversion_result, seed=42)
        definition = builder.build()
        
        assert len(definition.relationship_types) == 1
        assert definition.relationship_types[0].name == "produces"
    
    def test_maps_types_correctly(self, sample_entity_type_with_decimal):
        """Test that types are mapped correctly (Decimal -> Double)."""
        result = ConversionResult(
            entity_types=[sample_entity_type_with_decimal],
            relationship_types=[],
        )
        
        builder = ttl_to_sdk_builder(result, seed=42)
        definition = builder.build()
        
        entity = definition.entity_types[0]
        props_by_name = {p.name: p for p in entity.properties}
        
        # Decimal should be mapped to Double
        assert props_by_name["Price"].data_type.value == "Double"
        # Float should stay Float (SDK has separate Float type)
        assert props_by_name["Weight"].data_type.value == "Float"
    
    def test_marks_key_property(self, sample_entity_type):
        """Test that key property is marked correctly."""
        result = ConversionResult(
            entity_types=[sample_entity_type],
            relationship_types=[],
        )
        
        builder = ttl_to_sdk_builder(result, seed=42)
        definition = builder.build()
        
        entity = definition.entity_types[0]
        assert len(entity.key_property_ids) == 1
    
    def test_with_seed_reproducible(self, sample_conversion_result):
        """Test that seed produces reproducible IDs."""
        builder1 = ttl_to_sdk_builder(sample_conversion_result, seed=42)
        builder2 = ttl_to_sdk_builder(sample_conversion_result, seed=42)
        
        def1 = builder1.build()
        def2 = builder2.build()
        
        assert def1.entity_types[0].id == def2.entity_types[0].id


# =============================================================================
# ttl_result_to_sdk_infos Tests
# =============================================================================

class TestTtlResultToSdkInfos:
    """Tests for ttl_result_to_sdk_infos function."""
    
    def test_converts_all_entities(self, sample_conversion_result):
        """Test that all entities are converted."""
        entity_infos, rel_infos = ttl_result_to_sdk_infos(sample_conversion_result)
        
        assert len(entity_infos) == 2
        assert all(isinstance(e, TTLEntityInfo) for e in entity_infos)
    
    def test_converts_valid_relationships(self, sample_conversion_result):
        """Test that valid relationships are converted."""
        entity_infos, rel_infos = ttl_result_to_sdk_infos(sample_conversion_result)
        
        assert len(rel_infos) == 1
        assert rel_infos[0].name == "produces"
    
    def test_skips_invalid_relationships(self):
        """Test that relationships with unknown entities are skipped."""
        entity = EntityType(
            id="1000000000001",
            name="OnlyEntity",
            properties=[],
        )
        relationship = RelationshipType(
            id="2000000000001",
            name="orphan",
            source=RelationshipEnd(entity_type_id="1000000000001"),
            target=RelationshipEnd(entity_type_id="9999999999999"),  # Unknown
        )
        
        result = ConversionResult(
            entity_types=[entity],
            relationship_types=[relationship],
        )
        
        entity_infos, rel_infos = ttl_result_to_sdk_infos(result)
        
        assert len(entity_infos) == 1
        assert len(rel_infos) == 0  # Orphan relationship skipped


# =============================================================================
# create_bridge_from_ttl Tests
# =============================================================================

class TestCreateBridgeFromTtl:
    """Tests for create_bridge_from_ttl function."""
    
    def test_creates_bridge(self, sample_conversion_result, workspace_id, lakehouse_id):
        """Test that bridge is created with entities."""
        bridge = create_bridge_from_ttl(
            conversion_result=sample_conversion_result,
            workspace_id=workspace_id,
            lakehouse_id=lakehouse_id,
            seed=42,
        )
        
        assert bridge is not None
        assert bridge.workspace_id == workspace_id
        assert bridge.lakehouse_id == lakehouse_id
    
    def test_bridge_has_entities(self, sample_conversion_result, workspace_id, lakehouse_id):
        """Test that bridge has all entities from TTL."""
        bridge = create_bridge_from_ttl(
            conversion_result=sample_conversion_result,
            workspace_id=workspace_id,
            lakehouse_id=lakehouse_id,
            seed=42,
        )
        
        # Build and check
        definition = bridge.build()
        
        assert len(definition.entity_types) == 2
    
    def test_bridge_has_relationships(self, sample_conversion_result, workspace_id, lakehouse_id):
        """Test that bridge has relationships from TTL."""
        bridge = create_bridge_from_ttl(
            conversion_result=sample_conversion_result,
            workspace_id=workspace_id,
            lakehouse_id=lakehouse_id,
            seed=42,
        )
        
        # Build and check
        definition = bridge.build()
        
        assert len(definition.relationship_types) == 1
    
    def test_bridge_with_eventhouse(self, sample_conversion_result, workspace_id):
        """Test bridge creation with eventhouse configuration."""
        bridge = create_bridge_from_ttl(
            conversion_result=sample_conversion_result,
            workspace_id=workspace_id,
            eventhouse_id="eventhouse-123",
            database_name="TestDB",
            cluster_uri="https://test.kusto.com",
            seed=42,
        )
        
        assert bridge.eventhouse_id == "eventhouse-123"
        assert bridge.database_name == "TestDB"
        assert bridge.cluster_uri == "https://test.kusto.com"


# =============================================================================
# Integration Tests
# =============================================================================

class TestSdkConverterIntegration:
    """Integration tests for complete workflows."""
    
    def test_full_conversion_workflow(self, sample_conversion_result, workspace_id, lakehouse_id):
        """Test complete TTL to SDK definition workflow."""
        # Step 1: Create bridge from TTL
        bridge = create_bridge_from_ttl(
            conversion_result=sample_conversion_result,
            workspace_id=workspace_id,
            lakehouse_id=lakehouse_id,
            seed=42,
        )
        
        # Step 2: Build definition
        definition = bridge.build()
        
        # Step 3: Verify structure
        assert len(definition.entity_types) == 2
        assert len(definition.relationship_types) == 1
        
        # Verify entity has correct properties
        facility = next(e for e in definition.entity_types if e.name == "Facility")
        assert len(facility.properties) == 4
        assert len(facility.key_property_ids) == 1
        
        # Verify relationship has correct source/target
        produces = definition.relationship_types[0]
        assert produces.name == "produces"
    
    def test_type_mapping_all_types(self):
        """Test that all TTL types are mapped correctly."""
        entity = EntityType(
            id="1",
            name="AllTypes",
            key_property_name="StringProp",
            properties=[
                EntityTypeProperty(id="1", name="StringProp", value_type="String"),
                EntityTypeProperty(id="2", name="BigIntProp", value_type="BigInt"),
                EntityTypeProperty(id="3", name="LongProp", value_type="Long"),
                EntityTypeProperty(id="4", name="IntProp", value_type="Int"),
                EntityTypeProperty(id="5", name="DoubleProp", value_type="Double"),
                EntityTypeProperty(id="6", name="FloatProp", value_type="Float"),
                EntityTypeProperty(id="7", name="DecimalProp", value_type="Decimal"),
                EntityTypeProperty(id="8", name="BooleanProp", value_type="Boolean"),
                EntityTypeProperty(id="9", name="DateTimeProp", value_type="DateTime"),
            ],
        )
        
        result = ConversionResult(entity_types=[entity], relationship_types=[])
        builder = ttl_to_sdk_builder(result, seed=42)
        definition = builder.build()
        
        props_by_name = {p.name: p for p in definition.entity_types[0].properties}
        
        assert props_by_name["StringProp"].data_type.value == "String"
        assert props_by_name["BigIntProp"].data_type.value == "BigInt"
        assert props_by_name["LongProp"].data_type.value == "BigInt"
        assert props_by_name["IntProp"].data_type.value == "BigInt"
        assert props_by_name["DoubleProp"].data_type.value == "Double"
        assert props_by_name["FloatProp"].data_type.value == "Float"
        assert props_by_name["DecimalProp"].data_type.value == "Double"
        assert props_by_name["BooleanProp"].data_type.value == "Boolean"
        assert props_by_name["DateTimeProp"].data_type.value == "DateTime"
