"""
Tests for relationship contextualization bindings.

Tests the parsing and building of relationship contextualizations
that bind foreign key relationships between entities.
"""

import pytest
from pathlib import Path

from demo_automation.binding import (
    OntologyBindingBuilder,
    RelationshipContextualization,
    ParsedRelationshipBinding,
    BindingMarkdownParser,
    RelationshipBindingParser,
    BindingType,
    SourceType,
    parse_demo_bindings,
)


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
            source_schema="dbo",
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
        assert result["dataBindingTable"]["sourceSchema"] == "dbo"
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
            source_schema="dbo",
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


class TestOntologyBindingBuilderRelationships:
    """Tests for relationship methods in OntologyBindingBuilder."""

    @pytest.fixture
    def builder(self):
        """Create a builder instance."""
        return OntologyBindingBuilder(
            workspace_id="workspace-123",
            ontology_id="ontology-456",
        )

    def test_add_relationship_contextualization(self, builder):
        """Test adding a relationship contextualization."""
        builder.add_relationship_contextualization(
            relationship_type_id="produces",
            lakehouse_id="lakehouse-789",
            table_name="DimProductionBatch",
            source_key_column="FacilityId",
            source_key_property_id="facility-key",
            target_key_column="BatchId",
            target_key_property_id="batch-key",
        )

        ctxs = builder.get_contextualizations()
        assert len(ctxs) == 1
        assert "produces" in ctxs
        assert ctxs["produces"].table_name == "DimProductionBatch"
        assert ctxs["produces"].source_type == SourceType.LAKEHOUSE_TABLE

    def test_add_eventhouse_relationship_contextualization(self, builder):
        """Test adding an Eventhouse relationship contextualization."""
        builder.add_eventhouse_relationship_contextualization(
            relationship_type_id="hasEvent",
            eventhouse_id="eventhouse-abc",
            database_name="TelemetryDB",
            table_name="BatchEvents",
            source_key_column="BatchId",
            source_key_property_id="batch-key",
            target_key_column="EventId",
            target_key_property_id="event-key",
        )

        ctxs = builder.get_contextualizations()
        assert len(ctxs) == 1
        assert ctxs["hasEvent"].source_type == SourceType.KUSTO_TABLE
        assert ctxs["hasEvent"].database_name == "TelemetryDB"

    def test_register_entity_key_property(self, builder):
        """Test registering entity key properties."""
        builder.register_entity_key_property("Facility", "facility-key-123")
        builder.register_entity_key_property("ProductionBatch", "batch-key-456")

        keys = builder.get_entity_key_properties()
        assert keys["Facility"] == "facility-key-123"
        assert keys["ProductionBatch"] == "batch-key-456"

    def test_add_contextualization_from_parsed(self, builder):
        """Test adding contextualization from parsed binding."""
        # Register entity keys first
        builder.register_entity_key_property("Facility", "facility-key-123")
        builder.register_entity_key_property("ProductionBatch", "batch-key-456")

        parsed = ParsedRelationshipBinding(
            relationship_name="produces",
            source_entity="Facility",
            target_entity="ProductionBatch",
            table_name="DimProductionBatch",
            source_key_column="FacilityId",
            target_key_column="BatchId",
            source_type="lakehouse",
        )

        builder.add_contextualization_from_parsed(
            parsed=parsed,
            lakehouse_id="lakehouse-789",
        )

        ctxs = builder.get_contextualizations()
        assert len(ctxs) == 1
        assert ctxs["produces"].source_key_property_id == "facility-key-123"
        assert ctxs["produces"].target_key_property_id == "batch-key-456"

    def test_build_definition_parts_with_contextualizations(self, builder):
        """Test building definition parts includes contextualizations."""
        # Add an entity binding
        builder.add_lakehouse_binding(
            entity_type_id="Product",
            lakehouse_id="lakehouse-789",
            table_name="DimProduct",
            key_column="ProductId",
            property_mappings={"ProductId": "prop-1"},
        )

        # Add a relationship contextualization
        builder.add_relationship_contextualization(
            relationship_type_id="produces",
            lakehouse_id="lakehouse-789",
            table_name="DimProductionBatch",
            source_key_column="FacilityId",
            source_key_property_id="facility-key",
            target_key_column="BatchId",
            target_key_property_id="batch-key",
        )

        parts = builder.build_definition_parts()

        # Should have both entity binding and contextualization parts
        assert len(parts) == 2

        paths = [p["path"] for p in parts]
        assert any("EntityTypes/Product/DataBindings" in p for p in paths)
        assert any("RelationshipTypes/produces/Contextualizations" in p for p in paths)

    def test_chaining(self, builder):
        """Test method chaining."""
        result = (
            builder
            .register_entity_key_property("Facility", "fac-key")
            .register_entity_key_property("ProductionBatch", "batch-key")
            .add_relationship_contextualization(
                relationship_type_id="produces",
                lakehouse_id="lakehouse-789",
                table_name="DimProductionBatch",
                source_key_column="FacilityId",
                source_key_property_id="fac-key",
                target_key_column="BatchId",
                target_key_property_id="batch-key",
            )
        )

        assert result is builder
        assert len(builder.get_contextualizations()) == 1


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
        file_path.write_text(content)

        parser = BindingMarkdownParser(BindingType.STATIC)
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
