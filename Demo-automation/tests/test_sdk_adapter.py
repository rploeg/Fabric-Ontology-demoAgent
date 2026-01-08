"""
Tests for SDK adapter module.

Verifies the integration between Demo-automation and Fabric Ontology SDK.
"""

import pytest
from demo_automation.sdk_adapter import (
    map_ttl_type_to_sdk,
    map_ttl_type_to_string,
    TTL_TO_SDK_TYPE_MAP,
    create_ontology_builder,
    create_validator,
    validate_entity_name,
    validate_property_name,
    validate_relationship_name,
    validate_sdk_data_type,
)
from fabric_ontology.models import PropertyDataType
from fabric_ontology.exceptions import ValidationError as SDKValidationError


class TestTypeMapping:
    """Tests for TTL to SDK type mapping."""
    
    def test_string_type_mapping(self):
        """Test String type maps correctly."""
        assert map_ttl_type_to_sdk("String") == PropertyDataType.STRING
        assert map_ttl_type_to_sdk("string") == PropertyDataType.STRING
    
    def test_integer_type_mapping(self):
        """Test integer types map to Int64."""
        assert map_ttl_type_to_sdk("BigInt") == PropertyDataType.INT64
        assert map_ttl_type_to_sdk("Long") == PropertyDataType.INT64
        assert map_ttl_type_to_sdk("Int") == PropertyDataType.INT64
        assert map_ttl_type_to_sdk("Int64") == PropertyDataType.INT64
    
    def test_float_type_mapping(self):
        """Test float types map to Double."""
        assert map_ttl_type_to_sdk("Double") == PropertyDataType.DOUBLE
        assert map_ttl_type_to_sdk("Float") == PropertyDataType.DOUBLE
    
    def test_decimal_maps_to_double(self):
        """Test Decimal maps to Double (Decimal returns NULL in Graph)."""
        assert map_ttl_type_to_sdk("Decimal") == PropertyDataType.DOUBLE
        assert map_ttl_type_to_sdk("decimal") == PropertyDataType.DOUBLE
    
    def test_boolean_type_mapping(self):
        """Test Boolean type maps correctly."""
        assert map_ttl_type_to_sdk("Boolean") == PropertyDataType.BOOLEAN
        assert map_ttl_type_to_sdk("boolean") == PropertyDataType.BOOLEAN
    
    def test_datetime_type_mapping(self):
        """Test DateTime types map correctly."""
        assert map_ttl_type_to_sdk("DateTime") == PropertyDataType.DATETIME
        assert map_ttl_type_to_sdk("Date") == PropertyDataType.DATETIME
        assert map_ttl_type_to_sdk("DateTimeOffset") == PropertyDataType.DATETIMEOFFSET
    
    def test_unknown_type_defaults_to_string(self):
        """Test unknown types default to String."""
        assert map_ttl_type_to_sdk("UnknownType") == PropertyDataType.STRING
        assert map_ttl_type_to_sdk("CustomType") == PropertyDataType.STRING
    
    def test_map_to_string_returns_string(self):
        """Test map_ttl_type_to_string returns string value."""
        assert map_ttl_type_to_string("String") == "String"
        assert map_ttl_type_to_string("BigInt") == "Int64"
        assert map_ttl_type_to_string("Double") == "Double"
        assert map_ttl_type_to_string("Boolean") == "Boolean"


class TestOntologyBuilder:
    """Tests for SDK builder creation."""
    
    def test_create_builder(self):
        """Test creating an ontology builder."""
        builder = create_ontology_builder()
        assert builder is not None
    
    def test_create_builder_with_seed(self):
        """Test creating builder with seed for reproducible IDs."""
        builder1 = create_ontology_builder(seed=12345)
        builder2 = create_ontology_builder(seed=12345)
        
        # Build entities with same seed should get same IDs
        builder1.add_entity_type("TestEntity").add_property("EntityId", "String", is_key=True).done()
        builder2.add_entity_type("TestEntity").add_property("EntityId", "String", is_key=True).done()
        
        def1 = builder1.build()
        def2 = builder2.build()
        
        assert def1.entity_types[0].id == def2.entity_types[0].id
    
    def test_builder_fluent_api(self):
        """Test builder fluent API works correctly."""
        builder = create_ontology_builder()
        
        builder.add_entity_type("Equipment") \
            .add_property("EquipmentId", "String", is_key=True) \
            .add_property("Name", "String") \
            .add_property("Status", "String") \
            .done()
        
        definition = builder.build()
        
        assert len(definition.entity_types) == 1
        assert definition.entity_types[0].name == "Equipment"
        assert len(definition.entity_types[0].properties) == 3


class TestValidator:
    """Tests for SDK validation wrappers."""
    
    def test_create_validator(self):
        """Test creating a validator."""
        validator = create_validator(strict=True)
        assert validator is not None
        assert validator.strict == True
    
    def test_validate_valid_entity_name(self):
        """Test validation passes for valid entity names."""
        # Should not raise
        validate_entity_name("Equipment")
        validate_entity_name("ProductionBatch")
        validate_entity_name("My_Entity_123")
    
    def test_validate_invalid_entity_name_reserved_word(self):
        """Test validation fails for GQL reserved words."""
        with pytest.raises(SDKValidationError) as exc_info:
            validate_entity_name("match")
        assert "reserved" in str(exc_info.value).lower()
    
    def test_validate_invalid_entity_name_starts_with_number(self):
        """Test validation fails for names starting with numbers."""
        with pytest.raises(SDKValidationError):
            validate_entity_name("123Entity")
    
    def test_validate_valid_property_name(self):
        """Test validation passes for valid property names."""
        validate_property_name("EquipmentId")
        validate_property_name("DisplayName")
        validate_property_name("created_at")
    
    def test_validate_invalid_property_name(self):
        """Test validation fails for reserved property names."""
        with pytest.raises(SDKValidationError):
            validate_property_name("return")
    
    def test_validate_valid_relationship_name(self):
        """Test validation passes for valid relationship names."""
        validate_relationship_name("hasEquipment")
        validate_relationship_name("belongsTo")
        validate_relationship_name("produces")
    
    def test_validate_invalid_relationship_name(self):
        """Test validation fails for reserved relationship names."""
        with pytest.raises(SDKValidationError):
            validate_relationship_name("contains")  # GQL reserved
    
    def test_validate_valid_data_type(self):
        """Test validation passes for valid data types."""
        validate_sdk_data_type("String")
        validate_sdk_data_type("Int64")
        validate_sdk_data_type("Double")
        validate_sdk_data_type("Boolean")
        validate_sdk_data_type("DateTime")
    
    def test_validate_decimal_type_rejected(self):
        """Test validation rejects Decimal type."""
        with pytest.raises(SDKValidationError) as exc_info:
            validate_sdk_data_type("Decimal")
        assert "decimal" in str(exc_info.value).lower()


class TestEndToEndBuilder:
    """End-to-end tests for building ontology definitions."""
    
    def test_build_simple_ontology(self):
        """Test building a simple ontology with entity and relationship."""
        builder = create_ontology_builder()
        
        # Add Facility entity
        builder.add_entity_type("Facility") \
            .add_property("FacilityId", "String", is_key=True) \
            .add_property("Name", "String") \
            .add_property("Location", "String") \
            .done()
        
        # Add Equipment entity
        builder.add_entity_type("Equipment") \
            .add_property("EquipmentId", "String", is_key=True) \
            .add_property("Model", "String") \
            .add_property("Status", "String") \
            .done()
        
        # Add relationship
        builder.add_relationship_type("hasEquipment", "Facility", "Equipment").done()
        
        # Build and validate
        definition = builder.build()
        
        assert len(definition.entity_types) == 2
        assert len(definition.relationship_types) == 1
        
        # Verify entity type format
        facility = definition.get_entity_type_by_name("Facility")
        assert facility is not None
        entity_dict = facility.to_definition_dict()
        
        # Check official API format requirements
        assert entity_dict["namespace"] == "usertypes"
        assert entity_dict["namespaceType"] == "Custom"
        assert entity_dict["visibility"] == "Visible"
        assert "entityIdParts" in entity_dict
        
        # Verify relationship format
        rel = definition.relationship_types[0]
        rel_dict = rel.to_definition_dict()
        
        # Check nested source/target
        assert "source" in rel_dict
        assert "target" in rel_dict
        assert "entityTypeId" in rel_dict["source"]
        assert "entityTypeId" in rel_dict["target"]
    
    def test_build_ontology_with_timeseries_properties(self):
        """Test building entity with timeseries properties."""
        builder = create_ontology_builder()
        
        builder.add_entity_type("Sensor") \
            .add_property("SensorId", "String", is_key=True) \
            .add_property("Name", "String") \
            .add_timeseries_property("Temperature", "Double") \
            .add_timeseries_property("Humidity", "Double") \
            .done()
        
        definition = builder.build()
        sensor = definition.entity_types[0]
        entity_dict = sensor.to_definition_dict()
        
        # Check properties are separated
        assert len(entity_dict["properties"]) == 2  # SensorId, Name
        assert "timeseriesProperties" in entity_dict
        assert len(entity_dict["timeseriesProperties"]) == 2  # Temperature, Humidity
