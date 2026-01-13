"""
Tests for SDK Binding Bridge.

Tests the SDKBindingBridge module which bridges Demo-automation
parsed bindings to SDK OntologyBuilder.
"""

import pytest
from unittest.mock import MagicMock, patch

from demo_automation.binding.sdk_binding_bridge import (
    SDKBindingBridge,
    EntityBindingConfig,
    RelationshipContextConfig,
    TTLEntityInfo,
    TTLRelationshipInfo,
    create_binding_bridge,
    bridge_parsed_entity_to_config,
    bridge_parsed_relationship_to_config,
)
from demo_automation.binding.binding_parser import (
    ParsedEntityBinding,
    ParsedPropertyMapping,
    BindingType,
)
from demo_automation.binding.binding_builder import ParsedRelationshipBinding


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def workspace_id():
    """Sample workspace ID."""
    return "12345678-1234-1234-1234-123456789012"


@pytest.fixture
def lakehouse_id():
    """Sample lakehouse ID."""
    return "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


@pytest.fixture
def eventhouse_id():
    """Sample eventhouse ID."""
    return "11111111-2222-3333-4444-555555555555"


@pytest.fixture
def cluster_uri():
    """Sample cluster URI."""
    return "https://test-cluster.kusto.fabric.microsoft.com"


@pytest.fixture
def basic_bridge(workspace_id, lakehouse_id):
    """Create a basic bridge with just lakehouse."""
    return SDKBindingBridge(
        workspace_id=workspace_id,
        lakehouse_id=lakehouse_id,
        seed=42,  # Fixed seed for reproducible tests
    )


@pytest.fixture
def full_bridge(workspace_id, lakehouse_id, eventhouse_id, cluster_uri):
    """Create a bridge with both lakehouse and eventhouse."""
    return SDKBindingBridge(
        workspace_id=workspace_id,
        lakehouse_id=lakehouse_id,
        eventhouse_id=eventhouse_id,
        database_name="TestDB",
        cluster_uri=cluster_uri,
        seed=42,
    )


@pytest.fixture
def sample_ttl_entity():
    """Sample TTL entity info."""
    return TTLEntityInfo(
        name="Facility",
        properties=[
            {"name": "FacilityId", "value_type": "String", "is_key": True},
            {"name": "FacilityName", "value_type": "String"},
            {"name": "Capacity", "value_type": "BigInt"},
        ],
        key_property_name="FacilityId",
    )


@pytest.fixture
def sample_static_binding():
    """Sample static (lakehouse) binding config."""
    return EntityBindingConfig(
        entity_name="Facility",
        binding_type="static",
        table_name="DimFacility",
        key_column="FacilityId",
        column_mappings={
            "FacilityId": "FacilityId",
            "FacilityName": "FacilityName",
            "Capacity": "Capacity",
        },
    )


@pytest.fixture
def sample_timeseries_binding():
    """Sample time-series (eventhouse) binding config."""
    return EntityBindingConfig(
        entity_name="Facility",
        binding_type="timeseries",
        table_name="FacilityTelemetry",
        key_column="FacilityId",
        timestamp_column="Timestamp",
        column_mappings={
            "Temperature": "Temperature",
            "Humidity": "Humidity",
        },
    )


@pytest.fixture
def sample_relationship_context():
    """Sample relationship context config."""
    return RelationshipContextConfig(
        relationship_name="produces",
        source_entity="Facility",
        target_entity="ProductionBatch",
        source_type="lakehouse",
        table_name="DimProductionBatch",
        source_key_column="FacilityId",
        target_key_column="BatchId",
    )


# =============================================================================
# SDKBindingBridge Basic Tests
# =============================================================================

class TestSDKBindingBridgeInit:
    """Test SDKBindingBridge initialization."""
    
    def test_init_basic(self, workspace_id, lakehouse_id):
        """Test basic initialization."""
        bridge = SDKBindingBridge(
            workspace_id=workspace_id,
            lakehouse_id=lakehouse_id,
        )
        assert bridge.workspace_id == workspace_id
        assert bridge.lakehouse_id == lakehouse_id
        assert bridge.eventhouse_id is None
        assert bridge._builder is not None
    
    def test_init_full(self, workspace_id, lakehouse_id, eventhouse_id, cluster_uri):
        """Test full initialization with all parameters."""
        bridge = SDKBindingBridge(
            workspace_id=workspace_id,
            lakehouse_id=lakehouse_id,
            eventhouse_id=eventhouse_id,
            database_name="TestDB",
            cluster_uri=cluster_uri,
            seed=42,
        )
        assert bridge.workspace_id == workspace_id
        assert bridge.lakehouse_id == lakehouse_id
        assert bridge.eventhouse_id == eventhouse_id
        assert bridge.database_name == "TestDB"
        assert bridge.cluster_uri == cluster_uri


class TestSDKBindingBridgeAddEntityType:
    """Test adding entity types."""
    
    def test_add_entity_type_basic(self, basic_bridge):
        """Test adding a basic entity type."""
        builder = basic_bridge.add_entity_type(
            name="Facility",
            properties=[
                {"name": "FacilityId", "value_type": "String", "is_key": True},
                {"name": "FacilityName", "value_type": "String"},
            ],
        )
        assert builder is not None
        assert builder._name == "Facility"
        assert len(builder._properties) == 2
    
    def test_add_entity_type_with_key_property_name(self, basic_bridge):
        """Test adding entity with key_property_name parameter."""
        builder = basic_bridge.add_entity_type(
            name="Supplier",
            properties=[
                {"name": "SupplierId", "value_type": "String"},
                {"name": "SupplierName", "value_type": "String"},
            ],
            key_property_name="SupplierId",
        )
        # Find the property marked as key
        key_props = [p for p in builder._properties if p.id in builder._key_property_ids]
        assert len(key_props) == 1
        assert key_props[0].name == "SupplierId"
    
    def test_add_entity_type_maps_types(self, basic_bridge):
        """Test that TTL types are mapped to SDK types."""
        builder = basic_bridge.add_entity_type(
            name="DataTypes",
            properties=[
                {"name": "StringProp", "value_type": "String"},
                {"name": "IntProp", "value_type": "BigInt"},
                {"name": "DoubleProp", "value_type": "Double"},
                {"name": "BoolProp", "value_type": "Boolean"},
                {"name": "DateProp", "value_type": "DateTime"},
            ],
        )
        # Verify types were mapped correctly
        prop_types = {p.name: p.data_type.value for p in builder._properties}
        assert prop_types["StringProp"] == "String"
        assert prop_types["IntProp"] == "BigInt"
        assert prop_types["DoubleProp"] == "Double"
        assert prop_types["BoolProp"] == "Boolean"
        assert prop_types["DateProp"] == "DateTime"


class TestSDKBindingBridgeAddEntityWithBinding:
    """Test adding entities with bindings."""
    
    def test_add_entity_with_lakehouse_binding(self, basic_bridge, sample_ttl_entity, sample_static_binding):
        """Test adding entity with lakehouse binding."""
        builder = basic_bridge.add_entity_with_binding(sample_ttl_entity, sample_static_binding)
        
        assert builder._name == "Facility"
        assert len(builder._data_bindings) == 1
        
        binding = builder._data_bindings[0]
        assert binding.binding is not None
    
    def test_add_entity_with_eventhouse_binding(self, full_bridge, sample_timeseries_binding):
        """Test adding entity with eventhouse binding."""
        ttl_entity = TTLEntityInfo(
            name="SensorData",
            properties=[
                {"name": "SensorId", "value_type": "String", "is_key": True},
                {"name": "Temperature", "value_type": "Double"},
                {"name": "Humidity", "value_type": "Double"},
            ],
            key_property_name="SensorId",
        )
        
        binding = EntityBindingConfig(
            entity_name="SensorData",
            binding_type="timeseries",
            table_name="SensorReadings",
            key_column="SensorId",
            timestamp_column="Timestamp",
            column_mappings={
                "Temperature": "Temperature",
                "Humidity": "Humidity",
            },
        )
        
        builder = full_bridge.add_entity_with_binding(ttl_entity, binding)
        
        assert builder._name == "SensorData"
        assert len(builder._data_bindings) == 1
    
    def test_add_entity_missing_lakehouse_warns(self, workspace_id, sample_ttl_entity, sample_static_binding):
        """Test warning when lakehouse ID is missing for static binding."""
        bridge = SDKBindingBridge(workspace_id=workspace_id)  # No lakehouse_id
        
        # Should still create entity, just without binding
        builder = bridge.add_entity_with_binding(sample_ttl_entity, sample_static_binding)
        assert builder._name == "Facility"
        assert len(builder._data_bindings) == 0


class TestSDKBindingBridgeAddRelationship:
    """Test adding relationships."""
    
    def test_add_relationship_type(self, basic_bridge, sample_ttl_entity, sample_static_binding):
        """Test adding a relationship type."""
        # First add entities
        basic_bridge.add_entity_with_binding(sample_ttl_entity, sample_static_binding)
        
        # Add target entity
        target_entity = TTLEntityInfo(
            name="ProductionBatch",
            properties=[
                {"name": "BatchId", "value_type": "String", "is_key": True},
                {"name": "BatchName", "value_type": "String"},
            ],
        )
        target_binding = EntityBindingConfig(
            entity_name="ProductionBatch",
            binding_type="static",
            table_name="DimProductionBatch",
            key_column="BatchId",
            column_mappings={"BatchId": "BatchId", "BatchName": "BatchName"},
        )
        basic_bridge.add_entity_with_binding(target_entity, target_binding)
        
        # Add relationship
        rel_builder = basic_bridge.add_relationship_type(
            name="produces",
            source_entity="Facility",
            target_entity="ProductionBatch",
        )
        
        assert rel_builder._name == "produces"
        assert rel_builder._source_entity_name == "Facility"
        assert rel_builder._target_entity_name == "ProductionBatch"
    
    def test_add_relationship_with_context(self, basic_bridge, sample_ttl_entity, sample_static_binding, sample_relationship_context):
        """Test adding relationship with contextualization."""
        # Add source entity
        basic_bridge.add_entity_with_binding(sample_ttl_entity, sample_static_binding)
        
        # Add target entity
        target_entity = TTLEntityInfo(
            name="ProductionBatch",
            properties=[
                {"name": "BatchId", "value_type": "String", "is_key": True},
            ],
        )
        target_binding = EntityBindingConfig(
            entity_name="ProductionBatch",
            binding_type="static",
            table_name="DimProductionBatch",
            key_column="BatchId",
            column_mappings={"BatchId": "BatchId"},
        )
        basic_bridge.add_entity_with_binding(target_entity, target_binding)
        
        # Add relationship with contextualization
        ttl_rel = TTLRelationshipInfo(
            name="produces",
            source_entity_name="Facility",
            target_entity_name="ProductionBatch",
        )
        
        rel_builder = basic_bridge.add_relationship_with_context(ttl_rel, sample_relationship_context)
        
        assert rel_builder._name == "produces"
        assert len(rel_builder._contextualizations) == 1


class TestSDKBindingBridgeBuild:
    """Test building ontology definitions."""
    
    def test_build_simple_ontology(self, basic_bridge, sample_ttl_entity, sample_static_binding):
        """Test building a simple ontology."""
        basic_bridge.add_entity_with_binding(sample_ttl_entity, sample_static_binding)
        
        definition = basic_bridge.build()
        
        assert len(definition.entity_types) == 1
        assert definition.entity_types[0].name == "Facility"
    
    def test_build_with_relationships(self, basic_bridge, sample_ttl_entity, sample_static_binding):
        """Test building ontology with relationships."""
        # Add entities
        basic_bridge.add_entity_with_binding(sample_ttl_entity, sample_static_binding)
        
        target_entity = TTLEntityInfo(
            name="ProductionBatch",
            properties=[{"name": "BatchId", "value_type": "String", "is_key": True}],
        )
        target_binding = EntityBindingConfig(
            entity_name="ProductionBatch",
            binding_type="static",
            table_name="DimProductionBatch",
            key_column="BatchId",
            column_mappings={"BatchId": "BatchId"},
        )
        basic_bridge.add_entity_with_binding(target_entity, target_binding)
        
        # Add relationship
        rel_builder = basic_bridge.add_relationship_type("produces", "Facility", "ProductionBatch")
        rel_builder.done()
        
        definition = basic_bridge.build()
        
        assert len(definition.entity_types) == 2
        assert len(definition.relationship_types) == 1
        assert definition.relationship_types[0].name == "produces"


# =============================================================================
# Configuration Class Tests
# =============================================================================

class TestEntityBindingConfig:
    """Test EntityBindingConfig class."""
    
    def test_from_parsed_static(self):
        """Test creating config from parsed static binding."""
        parsed = ParsedEntityBinding(
            entity_name="Facility",
            table_name="DimFacility",
            key_column="FacilityId",
            binding_type=BindingType.STATIC,
            property_mappings=[
                ParsedPropertyMapping(source_column="FacilityId", target_property="FacilityId"),
                ParsedPropertyMapping(source_column="Name", target_property="FacilityName"),
            ],
        )
        
        config = EntityBindingConfig.from_parsed(parsed)
        
        assert config.entity_name == "Facility"
        assert config.binding_type == "static"
        assert config.table_name == "DimFacility"
        assert config.key_column == "FacilityId"
        assert len(config.column_mappings) == 2
        assert config.column_mappings["FacilityId"] == "FacilityId"
    
    def test_from_parsed_timeseries(self):
        """Test creating config from parsed timeseries binding."""
        parsed = ParsedEntityBinding(
            entity_name="Sensor",
            table_name="SensorData",
            key_column="SensorId",
            timestamp_column="Timestamp",
            binding_type=BindingType.TIMESERIES,
            property_mappings=[
                ParsedPropertyMapping(source_column="Value", target_property="Reading"),
            ],
        )
        
        config = EntityBindingConfig.from_parsed(parsed)
        
        assert config.binding_type == "timeseries"
        assert config.timestamp_column == "Timestamp"


class TestRelationshipContextConfig:
    """Test RelationshipContextConfig class."""
    
    def test_from_parsed(self):
        """Test creating config from parsed relationship binding."""
        parsed = ParsedRelationshipBinding(
            relationship_name="produces",
            source_entity="Facility",
            target_entity="ProductionBatch",
            table_name="DimProductionBatch",
            source_key_column="FacilityId",
            target_key_column="BatchId",
            source_type="lakehouse",
        )
        
        config = RelationshipContextConfig.from_parsed(parsed)
        
        assert config.relationship_name == "produces"
        assert config.source_entity == "Facility"
        assert config.target_entity == "ProductionBatch"
        assert config.table_name == "DimProductionBatch"
        assert config.source_key_column == "FacilityId"
        assert config.target_key_column == "BatchId"


# =============================================================================
# Factory Function Tests
# =============================================================================

class TestFactoryFunctions:
    """Test factory and bridge functions."""
    
    def test_create_binding_bridge(self, workspace_id, lakehouse_id):
        """Test create_binding_bridge factory."""
        bridge = create_binding_bridge(
            workspace_id=workspace_id,
            lakehouse_id=lakehouse_id,
        )
        
        assert isinstance(bridge, SDKBindingBridge)
        assert bridge.workspace_id == workspace_id
        assert bridge.lakehouse_id == lakehouse_id
    
    def test_bridge_parsed_entity_to_config(self):
        """Test bridging parsed entity binding to config."""
        parsed = ParsedEntityBinding(
            entity_name="Test",
            table_name="TestTable",
            key_column="Id",
            binding_type=BindingType.STATIC,
            property_mappings=[],
        )
        
        config = bridge_parsed_entity_to_config(parsed)
        
        assert isinstance(config, EntityBindingConfig)
        assert config.entity_name == "Test"
    
    def test_bridge_parsed_entity_to_config_timeseries(self):
        """Test bridging parsed timeseries binding with extra params."""
        parsed = ParsedEntityBinding(
            entity_name="Telemetry",
            table_name="TelemetryData",
            key_column="DeviceId",
            timestamp_column="Timestamp",
            binding_type=BindingType.TIMESERIES,
            property_mappings=[],
        )
        
        config = bridge_parsed_entity_to_config(
            parsed,
            database_name="TelemetryDB",
            cluster_uri="https://test.kusto.com",
        )
        
        assert config.database_name == "TelemetryDB"
        assert config.cluster_uri == "https://test.kusto.com"
    
    def test_bridge_parsed_relationship_to_config(self):
        """Test bridging parsed relationship binding to config."""
        parsed = ParsedRelationshipBinding(
            relationship_name="contains",
            source_entity="A",
            target_entity="B",
            table_name="EdgeAB",
            source_key_column="AId",
            target_key_column="BId",
            source_type="lakehouse",
        )
        
        config = bridge_parsed_relationship_to_config(parsed)
        
        assert isinstance(config, RelationshipContextConfig)
        assert config.relationship_name == "contains"


# =============================================================================
# Integration Tests
# =============================================================================

class TestSDKBindingBridgeIntegration:
    """Integration tests for complete workflows."""
    
    def test_complete_workflow(self, full_bridge):
        """Test complete workflow with multiple entities and relationships."""
        # Add Facility entity with static binding
        facility_entity = TTLEntityInfo(
            name="Facility",
            properties=[
                {"name": "FacilityId", "value_type": "String", "is_key": True},
                {"name": "Name", "value_type": "String"},
                {"name": "Location", "value_type": "String"},
            ],
        )
        facility_binding = EntityBindingConfig(
            entity_name="Facility",
            binding_type="static",
            table_name="DimFacility",
            key_column="FacilityId",
            column_mappings={
                "FacilityId": "FacilityId",
                "Name": "FacilityName",
                "Location": "Location",
            },
        )
        full_bridge.add_entity_with_binding(facility_entity, facility_binding)
        
        # Add Supplier entity
        supplier_entity = TTLEntityInfo(
            name="Supplier",
            properties=[
                {"name": "SupplierId", "value_type": "String", "is_key": True},
                {"name": "SupplierName", "value_type": "String"},
            ],
        )
        supplier_binding = EntityBindingConfig(
            entity_name="Supplier",
            binding_type="static",
            table_name="DimSupplier",
            key_column="SupplierId",
            column_mappings={
                "SupplierId": "SupplierId",
                "SupplierName": "SupplierName",
            },
        )
        full_bridge.add_entity_with_binding(supplier_entity, supplier_binding)
        
        # Add relationship
        ttl_rel = TTLRelationshipInfo(
            name="suppliesTo",
            source_entity_name="Supplier",
            target_entity_name="Facility",
        )
        context = RelationshipContextConfig(
            relationship_name="suppliesTo",
            source_entity="Supplier",
            target_entity="Facility",
            source_type="lakehouse",
            table_name="EdgeSupplierFacility",
            source_key_column="SupplierId",
            target_key_column="FacilityId",
        )
        rel_builder = full_bridge.add_relationship_with_context(ttl_rel, context)
        rel_builder.done()
        
        # Build definition
        definition = full_bridge.build()
        
        # Verify results
        assert len(definition.entity_types) == 2
        assert len(definition.relationship_types) == 1
        
        entity_names = [e.name for e in definition.entity_types]
        assert "Facility" in entity_names
        assert "Supplier" in entity_names
        
        assert definition.relationship_types[0].name == "suppliesTo"
    
    def test_get_builder(self, basic_bridge):
        """Test getting the underlying builder."""
        builder = basic_bridge.get_builder()
        assert builder is not None
        assert builder == basic_bridge._builder


# =============================================================================
# Timeseries Property Tests
# =============================================================================

class TestTimeseriesPropertyHandling:
    """Tests for timeseries property handling in SDK binding bridge."""
    
    def test_add_entity_with_eventhouse_properties(self, workspace_id, lakehouse_id, eventhouse_id, cluster_uri):
        """Test that eventhouse properties are added as timeseries properties."""
        # Create fresh bridge for this test
        bridge = SDKBindingBridge(
            workspace_id=workspace_id,
            lakehouse_id=lakehouse_id,
            eventhouse_id=eventhouse_id,
            database_name="TestDB",
            cluster_uri=cluster_uri,
            seed=42,
        )
        
        entity = TTLEntityInfo(
            name="SecurityAsset",
            properties=[
                {"name": "SecurityAssetId", "value_type": "String", "is_key": True},
                {"name": "SecurityAssetName", "value_type": "String"},
                {"name": "LastPrice", "value_type": "Double"},
                {"name": "BidPrice", "value_type": "Double"},
                {"name": "TradingVolume", "value_type": "BigInt"},
            ],
            key_property_name="SecurityAssetId",
        )
        
        # Define eventhouse properties (timeseries)
        eventhouse_props = {"LastPrice", "BidPrice", "TradingVolume"}
        
        binding = EntityBindingConfig(
            entity_name="SecurityAsset",
            binding_type="static",
            table_name="DimSecurityAsset",
            key_column="SecurityAssetId",
            column_mappings={"SecurityAssetId": "SecurityAssetId", "SecurityAssetName": "SecurityAssetName"},
        )
        
        bridge.add_entity_with_binding(entity, binding, eventhouse_properties=eventhouse_props)
        bridge.complete_all_entities()
        
        definition = bridge.build()
        
        # Find the SecurityAsset entity
        security_entity = None
        for e in definition.entity_types:
            if e.name == "SecurityAsset":
                security_entity = e
                break
        
        assert security_entity is not None
        
        # Check that static properties are in properties
        static_prop_names = [p.name for p in security_entity.properties]
        assert "SecurityAssetId" in static_prop_names
        assert "SecurityAssetName" in static_prop_names
        
        # Check that timeseries properties are in timeseries_properties
        timeseries_prop_names = [p.name for p in security_entity.timeseries_properties]
        assert "LastPrice" in timeseries_prop_names
        assert "BidPrice" in timeseries_prop_names
        assert "TradingVolume" in timeseries_prop_names
        
        # Timeseries properties should NOT be in static properties
        assert "LastPrice" not in static_prop_names
        assert "BidPrice" not in static_prop_names
        assert "TradingVolume" not in static_prop_names
    
    def test_add_entity_type_with_eventhouse_properties(self, workspace_id, lakehouse_id, eventhouse_id, cluster_uri):
        """Test add_entity_type with eventhouse_properties parameter."""
        # Create fresh bridge for this test
        bridge = SDKBindingBridge(
            workspace_id=workspace_id,
            lakehouse_id=lakehouse_id,
            eventhouse_id=eventhouse_id,
            database_name="TestDB",
            cluster_uri=cluster_uri,
            seed=100,
        )
        
        properties = [
            {"name": "TradeRecordId", "value_type": "String", "is_key": True},
            {"name": "TradePrice", "value_type": "Double"},
            {"name": "TradeLatency", "value_type": "Double"},
            {"name": "TradeMarketImpact", "value_type": "Double"},
        ]
        
        eventhouse_props = {"TradeLatency", "TradeMarketImpact"}
        
        bridge.add_entity_type(
            name="TradeRecord",
            properties=properties,
            key_property_name="TradeRecordId",
            eventhouse_properties=eventhouse_props,
        )
        # Don't call .done() - let build() handle it via complete_all_entities()
        
        definition = bridge.build()
        
        trade_entity = definition.entity_types[0]
        assert trade_entity.name == "TradeRecord"
        
        # TradeRecordId and TradePrice should be static
        static_names = [p.name for p in trade_entity.properties]
        assert "TradeRecordId" in static_names
        assert "TradePrice" in static_names
        
        # TradeLatency and TradeMarketImpact should be timeseries
        ts_names = [p.name for p in trade_entity.timeseries_properties]
        assert "TradeLatency" in ts_names
        assert "TradeMarketImpact" in ts_names
    
    def test_is_timeseries_flag_from_property(self, workspace_id, lakehouse_id, eventhouse_id, cluster_uri):
        """Test that is_timeseries flag in property dict is respected."""
        # Create fresh bridge for this test
        bridge = SDKBindingBridge(
            workspace_id=workspace_id,
            lakehouse_id=lakehouse_id,
            eventhouse_id=eventhouse_id,
            database_name="TestDB",
            cluster_uri=cluster_uri,
            seed=200,
        )
        
        properties = [
            {"name": "SensorDeviceId", "value_type": "String", "is_key": True},
            {"name": "TemperatureValue", "value_type": "Double", "is_timeseries": True},
            {"name": "HumidityValue", "value_type": "Double", "is_timeseries": True},
            {"name": "LocationName", "value_type": "String", "is_timeseries": False},
        ]
        
        bridge.add_entity_type(
            name="SensorDevice",
            properties=properties,
            key_property_name="SensorDeviceId",
        )
        # Don't call .done() - let build() handle it via complete_all_entities()
        
        definition = bridge.build()
        
        sensor = definition.entity_types[0]
        
        static_names = [p.name for p in sensor.properties]
        assert "SensorDeviceId" in static_names
        assert "LocationName" in static_names
        
        ts_names = [p.name for p in sensor.timeseries_properties]
        assert "TemperatureValue" in ts_names
        assert "HumidityValue" in ts_names
    
    def test_eventhouse_properties_override_is_timeseries_false(self, workspace_id, lakehouse_id, eventhouse_id, cluster_uri):
        """Test that eventhouse_properties set overrides is_timeseries=False."""
        # Create fresh bridge for this test
        bridge = SDKBindingBridge(
            workspace_id=workspace_id,
            lakehouse_id=lakehouse_id,
            eventhouse_id=eventhouse_id,
            database_name="TestDB",
            cluster_uri=cluster_uri,
            seed=300,
        )
        
        properties = [
            {"name": "DeviceUnitId", "value_type": "String", "is_key": True},
            {"name": "PowerConsumption", "value_type": "Double", "is_timeseries": False},  # Explicit false
        ]
        
        # But it's in eventhouse properties, so should be timeseries
        eventhouse_props = {"PowerConsumption"}
        
        bridge.add_entity_type(
            name="DeviceUnit",
            properties=properties,
            key_property_name="DeviceUnitId",
            eventhouse_properties=eventhouse_props,
        )
        # Don't call .done() - let build() handle it via complete_all_entities()
        
        definition = bridge.build()
        
        device = definition.entity_types[0]
        
        # PowerConsumption should be timeseries because it's in eventhouse_properties
        ts_names = [p.name for p in device.timeseries_properties]
        assert "PowerConsumption" in ts_names
    
    def test_no_eventhouse_properties_all_static(self, workspace_id, lakehouse_id):
        """Test that without eventhouse_properties, all are static."""
        # Create fresh bridge for this test (no eventhouse)
        bridge = SDKBindingBridge(
            workspace_id=workspace_id,
            lakehouse_id=lakehouse_id,
            seed=400,
        )
        
        properties = [
            {"name": "ProductItemId", "value_type": "String", "is_key": True},
            {"name": "ProductItemName", "value_type": "String"},
            {"name": "UnitPrice", "value_type": "Double"},
        ]
        
        bridge.add_entity_type(
            name="ProductItem",
            properties=properties,
            key_property_name="ProductItemId",
        )
        # Don't call .done() - let build() handle it via complete_all_entities()
        
        definition = bridge.build()
        
        product = definition.entity_types[0]
        
        static_names = [p.name for p in product.properties]
        assert len(static_names) == 3
        assert "ProductItemId" in static_names
        assert "ProductItemName" in static_names
        assert "UnitPrice" in static_names
        
        # No timeseries properties
        assert len(product.timeseries_properties) == 0
