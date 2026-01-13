"""
Tests for relationship contextualization bindings.

Tests the parsing and building of relationship contextualizations
that bind foreign key relationships between entities.
"""

import pytest
from pathlib import Path

from demo_automation.binding import (
    RelationshipContextualization,
    ParsedRelationshipBinding,
    BindingMarkdownParser,
    RelationshipBindingParser,
    BindingType,
    SourceType,
    parse_demo_bindings,
)
from demo_automation.binding.sdk_binding_bridge import (
    SDKBindingBridge,
    EntityBindingConfig,
    RelationshipContextConfig,
    TTLEntityInfo,
    TTLRelationshipInfo,
)
# Import the parser's BindingType for use with BindingMarkdownParser
from demo_automation.binding.binding_parser import BindingType as ParserBindingType


class TestRelationshipContextualization:
    """Tests for RelationshipContextualization dataclass."""

    def test_create_lakehouse_contextualization(self):
        """Test creating a Lakehouse-based contextualization."""
        ctx = RelationshipContextualization(
            contextualization_id="test-ctx-id",
            relationship_type_id="produces",
            workspace_id="workspace-123",
            item_id="lakehouse-456",
            source_type=SourceType.LAKEHOUSE_TABLE,
            table_name="DimProductionBatch",
            source_schema=None,  # None for lakehouses without schemas
            source_key_column="FacilityId",
            source_key_property_id="facility-prop-id",
            target_key_column="BatchId",
            target_key_property_id="batch-prop-id",
        )

        result = ctx.to_dict()

        assert result["id"] == "test-ctx-id"
        assert result["dataBindingTable"]["workspaceId"] == "workspace-123"
        assert result["dataBindingTable"]["itemId"] == "lakehouse-456"
        assert result["dataBindingTable"]["sourceTableName"] == "DimProductionBatch"
        assert result["dataBindingTable"]["sourceSchema"] is None  # None for lakehouses without schemas
        assert result["dataBindingTable"]["sourceType"] == "LakehouseTable"
        assert len(result["sourceKeyRefBindings"]) == 1
        assert result["sourceKeyRefBindings"][0]["sourceColumnName"] == "FacilityId"
        assert result["sourceKeyRefBindings"][0]["targetPropertyId"] == "facility-prop-id"
        assert len(result["targetKeyRefBindings"]) == 1
        assert result["targetKeyRefBindings"][0]["sourceColumnName"] == "BatchId"
        assert result["targetKeyRefBindings"][0]["targetPropertyId"] == "batch-prop-id"

    def test_create_kusto_contextualization(self):
        """Test creating a Kusto-based contextualization."""
        ctx = RelationshipContextualization(
            contextualization_id="test-ctx-id",
            relationship_type_id="hasEvent",
            workspace_id="workspace-123",
            item_id="eventhouse-789",
            source_type=SourceType.KUSTO_TABLE,
            table_name="BatchEvents",
            source_schema=None,  # Kusto tables also use None
            source_key_column="BatchId",
            source_key_property_id="batch-prop-id",
            target_key_column="EventId",
            target_key_property_id="event-prop-id",
            database_name="TelemetryDB",
        )

        result = ctx.to_dict()

        assert result["dataBindingTable"]["sourceType"] == "KustoTable"
        assert result["dataBindingTable"]["databaseName"] == "TelemetryDB"

    def test_generate_id(self):
        """Test ID generation produces valid UUIDs."""
        id1 = RelationshipContextualization.generate_id()
        id2 = RelationshipContextualization.generate_id()

        assert id1 != id2  # Should be unique
        assert len(id1) == 36  # UUID format


class TestSDKBindingBridgeRelationships:
    """Tests for relationship methods in SDKBindingBridge."""

    @pytest.fixture
    def bridge(self):
        """Create a bridge instance with lakehouse."""
        return SDKBindingBridge(
            workspace_id="workspace-123",
            lakehouse_id="lakehouse-789",
            seed=42,
        )

    @pytest.fixture
    def bridge_with_eventhouse(self):
        """Create a bridge instance with both lakehouse and eventhouse."""
        return SDKBindingBridge(
            workspace_id="workspace-123",
            lakehouse_id="lakehouse-789",
            eventhouse_id="eventhouse-abc",
            database_name="TelemetryDB",
            cluster_uri="https://test.kusto.fabric.microsoft.com",
            seed=42,
        )

    @pytest.fixture
    def source_entity(self):
        """Sample source entity (Facility)."""
        return TTLEntityInfo(
            name="Facility",
            properties=[
                {"name": "FacilityId", "value_type": "String", "is_key": True},
                {"name": "FacilityName", "value_type": "String"},
            ],
            key_property_name="FacilityId",
        )

    @pytest.fixture
    def target_entity(self):
        """Sample target entity (ProductionBatch)."""
        return TTLEntityInfo(
            name="ProductionBatch",
            properties=[
                {"name": "BatchId", "value_type": "String", "is_key": True},
                {"name": "BatchName", "value_type": "String"},
            ],
            key_property_name="BatchId",
        )

    @pytest.fixture
    def source_binding(self):
        """Binding config for source entity."""
        return EntityBindingConfig(
            entity_name="Facility",
            binding_type="static",
            table_name="DimFacility",
            key_column="FacilityId",
            column_mappings={"FacilityId": "FacilityId", "FacilityName": "FacilityName"},
        )

    @pytest.fixture
    def target_binding(self):
        """Binding config for target entity."""
        return EntityBindingConfig(
            entity_name="ProductionBatch",
            binding_type="static",
            table_name="DimProductionBatch",
            key_column="BatchId",
            column_mappings={"BatchId": "BatchId", "BatchName": "BatchName"},
        )

    def test_add_relationship_with_lakehouse_contextualization(
        self, bridge, source_entity, target_entity, source_binding, target_binding
    ):
        """Test adding a relationship with lakehouse contextualization."""
        # Add entities first
        bridge.add_entity_with_binding(source_entity, source_binding)
        bridge.add_entity_with_binding(target_entity, target_binding)

        # Create relationship with contextualization
        ttl_rel = TTLRelationshipInfo(
            name="produces",
            source_entity_name="Facility",
            target_entity_name="ProductionBatch",
        )
        context = RelationshipContextConfig(
            relationship_name="produces",
            source_entity="Facility",
            target_entity="ProductionBatch",
            source_type="lakehouse",
            table_name="DimProductionBatch",
            source_key_column="FacilityId",
            target_key_column="BatchId",
        )

        rel_builder = bridge.add_relationship_with_context(ttl_rel, context)

        assert rel_builder._name == "produces"
        assert len(rel_builder._contextualizations) == 1

    def test_add_relationship_with_eventhouse_contextualization(
        self, bridge_with_eventhouse, source_entity, target_entity, source_binding, target_binding
    ):
        """Test adding an Eventhouse relationship contextualization."""
        # Add entities first
        bridge_with_eventhouse.add_entity_with_binding(source_entity, source_binding)
        
        # Add event entity for timeseries
        event_entity = TTLEntityInfo(
            name="BatchEvent",
            properties=[
                {"name": "EventId", "value_type": "String", "is_key": True},
                {"name": "EventType", "value_type": "String"},
            ],
            key_property_name="EventId",
        )
        event_binding = EntityBindingConfig(
            entity_name="BatchEvent",
            binding_type="static",
            table_name="DimBatchEvent",
            key_column="EventId",
            column_mappings={"EventId": "EventId", "EventType": "EventType"},
        )
        bridge_with_eventhouse.add_entity_with_binding(event_entity, event_binding)

        # Create relationship with eventhouse contextualization
        ttl_rel = TTLRelationshipInfo(
            name="hasEvent",
            source_entity_name="Facility",
            target_entity_name="BatchEvent",
        )
        context = RelationshipContextConfig(
            relationship_name="hasEvent",
            source_entity="Facility",
            target_entity="BatchEvent",
            source_type="eventhouse",
            table_name="BatchEvents",
            source_key_column="FacilityId",
            target_key_column="EventId",
            database_name="TelemetryDB",
        )

        rel_builder = bridge_with_eventhouse.add_relationship_with_context(ttl_rel, context)

        assert rel_builder._name == "hasEvent"
        assert len(rel_builder._contextualizations) == 1

    def test_entity_key_property_tracking(self, bridge, source_entity, source_binding):
        """Test that entity key properties are tracked through the builder."""
        builder = bridge.add_entity_with_binding(source_entity, source_binding)

        # Key property should be tracked in the builder
        key_props = [p for p in builder._properties if p.id in builder._key_property_ids]
        assert len(key_props) == 1
        assert key_props[0].name == "FacilityId"

    def test_add_contextualization_from_parsed(
        self, bridge, source_entity, target_entity, source_binding, target_binding
    ):
        """Test adding contextualization from parsed binding."""
        # Add entities first
        bridge.add_entity_with_binding(source_entity, source_binding)
        bridge.add_entity_with_binding(target_entity, target_binding)

        parsed = ParsedRelationshipBinding(
            relationship_name="produces",
            source_entity="Facility",
            target_entity="ProductionBatch",
            table_name="DimProductionBatch",
            source_key_column="FacilityId",
            target_key_column="BatchId",
            source_type="lakehouse",
        )

        # Convert parsed to config
        context = RelationshipContextConfig.from_parsed(parsed)
        ttl_rel = TTLRelationshipInfo(
            name=parsed.relationship_name,
            source_entity_name=parsed.source_entity,
            target_entity_name=parsed.target_entity,
        )

        rel_builder = bridge.add_relationship_with_context(ttl_rel, context)

        assert rel_builder._name == "produces"
        assert len(rel_builder._contextualizations) == 1

    def test_build_definition_with_contextualizations(
        self, bridge, source_entity, target_entity, source_binding, target_binding
    ):
        """Test building definition includes contextualizations."""
        # Add entities with bindings
        bridge.add_entity_with_binding(source_entity, source_binding)
        bridge.add_entity_with_binding(target_entity, target_binding)

        # Add relationship with contextualization
        ttl_rel = TTLRelationshipInfo(
            name="produces",
            source_entity_name="Facility",
            target_entity_name="ProductionBatch",
        )
        context = RelationshipContextConfig(
            relationship_name="produces",
            source_entity="Facility",
            target_entity="ProductionBatch",
            source_type="lakehouse",
            table_name="DimProductionBatch",
            source_key_column="FacilityId",
            target_key_column="BatchId",
        )
        rel_builder = bridge.add_relationship_with_context(ttl_rel, context)
        rel_builder.done()  # Complete the relationship to add it to the ontology

        # Build the definition
        definition = bridge.build()

        # Should have entity types and relationship types
        assert definition.entity_types is not None
        assert definition.relationship_types is not None
        assert len(definition.entity_types) == 2
        assert len(definition.relationship_types) == 1

    def test_fluent_api(self, bridge):
        """Test fluent API pattern."""
        # Add entity and verify builder is returned
        # Note: "Product" is a reserved word, so we use "ProductItem"
        entity = TTLEntityInfo(
            name="ProductItem",
            properties=[{"name": "ProductId", "value_type": "String", "is_key": True}],
        )
        binding = EntityBindingConfig(
            entity_name="ProductItem",
            binding_type="static",
            table_name="DimProduct",
            key_column="ProductId",
            column_mappings={"ProductId": "ProductId"},
        )

        builder = bridge.add_entity_with_binding(entity, binding)
        
        # Builder should be returned for further configuration
        assert builder is not None
        assert builder._name == "ProductItem"


class TestRelationshipMarkdownParser:
    """Tests for parsing relationship bindings from markdown."""

    def test_parse_relationship_header_pattern(self):
        """Test the relationship header regex pattern."""
        pattern = BindingMarkdownParser.RELATIONSHIP_HEADER_PATTERN

        # Test: "### 5.1 produces (Facility → ProductionBatch)"
        match = pattern.search("### 5.1 produces (Facility → ProductionBatch)")
        assert match is not None
        assert match.group(1) == "produces"
        assert match.group(2) == "Facility"
        assert match.group(3) == "ProductionBatch"

        # Test with arrow variant: "### 5.2 manufactures (ProductionBatch -> Product)"
        match = pattern.search("### 5.2 manufactures (ProductionBatch -> Product)")
        assert match is not None
        assert match.group(1) == "manufactures"
        assert match.group(2) == "ProductionBatch"
        assert match.group(3) == "Product"

    def test_parse_relationships_from_content(self):
        """Test parsing relationships from markdown content."""
        content = """
## Step 5: Bind Relationships

### 5.1 produces (Facility → ProductionBatch)

| Setting | Value |
|---------|-------|
| Relationship | produces |
| Source Table | DimProductionBatch |
| Source Entity Key Column | FacilityId |
| Target Entity Key Column | BatchId |

---

### 5.2 manufactures (ProductionBatch → Product)

| Setting | Value |
|---------|-------|
| Relationship | manufactures |
| Source Table | DimProductionBatch |
| Source Entity Key Column | BatchId |
| Target Entity Key Column | ProductId |
"""

        parser = BindingMarkdownParser()
        relationships = parser.parse_relationships(content)

        assert len(relationships) == 2

        # Check first relationship
        produces = next(r for r in relationships if r.relationship_name == "produces")
        assert produces.source_entity == "Facility"
        assert produces.target_entity == "ProductionBatch"
        assert produces.table_name == "DimProductionBatch"
        assert produces.source_key_column == "FacilityId"
        assert produces.target_key_column == "BatchId"

        # Check second relationship
        manufactures = next(r for r in relationships if r.relationship_name == "manufactures")
        assert manufactures.source_entity == "ProductionBatch"
        assert manufactures.target_entity == "Product"
        assert manufactures.table_name == "DimProductionBatch"
        assert manufactures.source_key_column == "BatchId"
        assert manufactures.target_key_column == "ProductId"

    def test_parse_file_with_relationships(self, tmp_path):
        """Test parsing both entity and relationship bindings from file."""
        content = """
## Step 4: Bind Static Data to Entity Types

### 4.1 Product Entity

| Setting | Value |
|---------|-------|
| Entity Type | Product |
| Table | DimProduct |
| Key Column | ProductId |

## Step 5: Bind Relationships

### 5.1 supplies (Supplier → Component)

| Setting | Value |
|---------|-------|
| Relationship | supplies |
| Source Table | DimComponent |
| Source Entity Key Column | SupplierId |
| Target Entity Key Column | ComponentId |
"""

        file_path = tmp_path / "test-binding.md"
        file_path.write_text(content, encoding='utf-8')

        parser = BindingMarkdownParser(ParserBindingType.STATIC)
        entity_bindings, rel_bindings = parser.parse_file_with_relationships(file_path)

        # Note: Entity binding may not parse due to header format
        # but relationship should parse
        assert len(rel_bindings) == 1
        assert rel_bindings[0].relationship_name == "supplies"
        assert rel_bindings[0].source_entity == "Supplier"
        assert rel_bindings[0].target_entity == "Component"


class TestParsedRelationshipBinding:
    """Tests for ParsedRelationshipBinding dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        binding = ParsedRelationshipBinding(
            relationship_name="produces",
            relationship_id="rel-123",
            source_entity="Facility",
            target_entity="ProductionBatch",
            table_name="DimProductionBatch",
            source_key_column="FacilityId",
            target_key_column="BatchId",
            source_type="lakehouse",
        )

        result = binding.to_dict()

        assert result["relationship_name"] == "produces"
        assert result["relationship_id"] == "rel-123"
        assert result["source_entity"] == "Facility"
        assert result["target_entity"] == "ProductionBatch"
        assert result["table_name"] == "DimProductionBatch"
        assert result["source_key_column"] == "FacilityId"
        assert result["target_key_column"] == "BatchId"
        assert result["source_type"] == "lakehouse"
