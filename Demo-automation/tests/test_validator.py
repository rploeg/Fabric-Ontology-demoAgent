"""
Tests for the validator module.
"""

import pytest
from pathlib import Path

from demo_automation.validator import (
    DemoPackageValidator,
    ValidationSeverity,
    validate_demo_package,
)


class TestDemoPackageValidator:
    """Tests for DemoPackageValidator."""

    def test_validate_missing_directory(self, tmp_path):
        """Test validation of non-existent directory."""
        result = validate_demo_package(tmp_path / "nonexistent")

        assert not result.is_valid
        assert result.error_count > 0

    def test_validate_minimal_structure(self, tmp_path):
        """Test validation of minimal valid structure."""
        # Create minimal required structure
        demo_path = tmp_path / "TestDemo"
        demo_path.mkdir()
        (demo_path / "ontology").mkdir()
        (demo_path / "data").mkdir()
        (demo_path / "data" / "lakehouse").mkdir()

        # Create TTL file
        (demo_path / "ontology" / "test.ttl").write_text("# Test")

        # Create CSV file
        (demo_path / "data" / "lakehouse" / "test.csv").write_text("ID,Name\n1,Test\n")

        result = validate_demo_package(demo_path)

        # Should pass (may have warnings but no errors)
        assert result.is_valid

    def test_validate_missing_ontology(self, tmp_path):
        """Test validation fails without ontology."""
        demo_path = tmp_path / "TestDemo"
        demo_path.mkdir()
        (demo_path / "data").mkdir()

        result = validate_demo_package(demo_path)

        assert not result.is_valid
        assert any("ontology" in str(i).lower() for i in result.issues)

    def test_validate_missing_data(self, tmp_path):
        """Test validation fails without data directory."""
        demo_path = tmp_path / "TestDemo"
        demo_path.mkdir()
        (demo_path / "ontology").mkdir()

        result = validate_demo_package(demo_path)

        assert not result.is_valid

    def test_validate_empty_csv(self, tmp_path):
        """Test validation warns on empty CSV."""
        demo_path = tmp_path / "TestDemo"
        demo_path.mkdir()
        (demo_path / "ontology").mkdir()
        (demo_path / "data").mkdir()
        (demo_path / "data" / "lakehouse").mkdir()
        (demo_path / "ontology" / "test.ttl").write_text("# Test")

        # Create empty CSV
        (demo_path / "data" / "lakehouse" / "empty.csv").write_text("")

        result = validate_demo_package(demo_path)

        # Should have warning about empty CSV
        assert result.warning_count > 0 or result.error_count > 0

    def test_validate_csv_with_data(self, tmp_path):
        """Test validation passes with proper CSV."""
        demo_path = tmp_path / "TestDemo"
        demo_path.mkdir()
        (demo_path / "ontology").mkdir()
        (demo_path / "data").mkdir()
        (demo_path / "data" / "lakehouse").mkdir()
        (demo_path / "ontology" / "test.ttl").write_text("# Test")

        # Create valid CSV with ID column
        csv_content = "ProductID,Name,Price\n1,Widget,9.99\n2,Gadget,19.99\n"
        (demo_path / "data" / "lakehouse" / "products.csv").write_text(csv_content)

        result = validate_demo_package(demo_path)

        assert result.is_valid

    def test_validate_missing_bindings_warning(self, tmp_path):
        """Test validation warns about missing bindings."""
        demo_path = tmp_path / "TestDemo"
        demo_path.mkdir()
        (demo_path / "ontology").mkdir()
        (demo_path / "data").mkdir()
        (demo_path / "data" / "lakehouse").mkdir()
        (demo_path / "ontology" / "test.ttl").write_text("# Test")
        (demo_path / "data" / "lakehouse" / "test.csv").write_text("ID\n1\n")

        result = validate_demo_package(demo_path)

        # Should have warning about missing bindings
        assert any("binding" in str(i).lower() for i in result.issues)

    def test_validate_with_bindings(self, tmp_path):
        """Test validation with bindings directory."""
        demo_path = tmp_path / "TestDemo"
        demo_path.mkdir()
        (demo_path / "ontology").mkdir()
        (demo_path / "data").mkdir()
        (demo_path / "data" / "lakehouse").mkdir()
        (demo_path / "bindings").mkdir()
        (demo_path / "ontology" / "test.ttl").write_text("# Test")
        (demo_path / "data" / "lakehouse" / "test.csv").write_text("ID\n1\n")
        (demo_path / "bindings" / "lakehouse-binding.md").write_text("# Bindings")

        result = validate_demo_package(demo_path)

        assert result.is_valid


class TestValidationResult:
    """Tests for ValidationResult."""

    def test_is_valid_no_issues(self, tmp_path):
        """Test is_valid with no issues."""
        from demo_automation.validator import ValidationResult

        result = ValidationResult(demo_path=tmp_path)
        assert result.is_valid

    def test_is_valid_with_warning(self, tmp_path):
        """Test is_valid with only warnings."""
        from demo_automation.validator import ValidationResult

        result = ValidationResult(demo_path=tmp_path)
        result.add_warning("Test warning")

        assert result.is_valid  # Warnings don't fail validation

    def test_is_valid_with_error(self, tmp_path):
        """Test is_valid with error."""
        from demo_automation.validator import ValidationResult

        result = ValidationResult(demo_path=tmp_path)
        result.add_error("Test error")

        assert not result.is_valid


class TestTTLConstraints:
    """Tests for TTL file constraint validation."""

    def test_validate_xsd_decimal_error(self, tmp_path):
        """Test that xsd:decimal in TTL raises an error."""
        demo_path = tmp_path / "TestDemo"
        demo_path.mkdir()
        (demo_path / "ontology").mkdir()
        (demo_path / "data").mkdir()
        (demo_path / "data" / "lakehouse").mkdir()
        (demo_path / "data" / "lakehouse" / "test.csv").write_text("ID\n1\n")

        # Create TTL with xsd:decimal (not supported)
        ttl_content = """
        @prefix : <http://example.com/test#> .
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

        :Temperature a owl:DatatypeProperty ;
            rdfs:range xsd:decimal .
        """
        (demo_path / "ontology" / "test.ttl").write_text(ttl_content)

        result = validate_demo_package(demo_path)

        assert result.error_count > 0
        assert any("xsd:decimal" in str(i) for i in result.issues)

    def test_validate_xsd_double_passes(self, tmp_path):
        """Test that xsd:double in TTL is valid."""
        demo_path = tmp_path / "TestDemo"
        demo_path.mkdir()
        (demo_path / "ontology").mkdir()
        (demo_path / "data").mkdir()
        (demo_path / "data" / "lakehouse").mkdir()
        (demo_path / "data" / "lakehouse" / "test.csv").write_text("ID\n1\n")

        # Create TTL with xsd:double (supported)
        ttl_content = """
        @prefix : <http://example.com/test#> .
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

        :Temperature a owl:DatatypeProperty ;
            rdfs:range xsd:double .
        """
        (demo_path / "ontology" / "test.ttl").write_text(ttl_content)

        result = validate_demo_package(demo_path)

        # No errors about xsd:decimal
        assert not any("xsd:decimal" in str(i) for i in result.issues if i.severity.value == "error")


class TestRelationshipBindingValidation:
    """Tests for relationship binding validation rules."""

    def test_validate_relationship_target_key_mismatch(self, tmp_path):
        """Test that mismatched targetKeyColumn raises an error."""
        demo_path = tmp_path / "TestDemo"
        demo_path.mkdir()
        (demo_path / "ontology").mkdir()
        (demo_path / "data").mkdir()
        (demo_path / "data" / "lakehouse").mkdir()
        (demo_path / "bindings").mkdir()
        (demo_path / "ontology" / "test.ttl").write_text("# Test")

        # Create entity CSVs
        (demo_path / "data" / "lakehouse" / "DimCustomer.csv").write_text(
            "CustomerId,Name\nC001,Alice\nC002,Bob\n"
        )
        (demo_path / "data" / "lakehouse" / "DimOrder.csv").write_text(
            "OrderId,CustomerId,Total\nO001,C001,100\nO002,C002,200\n"
        )

        # Create bindings.yaml with WRONG targetKeyColumn name
        bindings_yaml = """
_schema_version: "1.0"

lakehouse:
  entities:
    - entity: Customer
      sourceTable: DimCustomer
      keyColumn: CustomerId
      properties:
        - property: CustomerId
          column: CustomerId
          type: string
        - property: Name
          column: Name
          type: string
    - entity: SalesOrder
      sourceTable: DimOrder
      keyColumn: OrderId
      properties:
        - property: OrderId
          column: OrderId
          type: string
        - property: Total
          column: Total
          type: double

  relationships:
    - relationship: PLACED
      sourceEntity: Customer
      targetEntity: SalesOrder
      sourceTable: DimOrder
      sourceKeyColumn: CustomerId
      targetKeyColumn: SalesOrderId  # WRONG - should be OrderId
"""
        (demo_path / "bindings" / "bindings.yaml").write_text(bindings_yaml)

        result = validate_demo_package(demo_path)

        # Should have error about targetKeyColumn mismatch
        assert any(
            "targetKeyColumn" in str(i) and "does NOT match" in str(i)
            for i in result.issues
        )

    def test_validate_relationship_source_key_mismatch(self, tmp_path):
        """Test that mismatched sourceKeyColumn raises an error."""
        demo_path = tmp_path / "TestDemo"
        demo_path.mkdir()
        (demo_path / "ontology").mkdir()
        (demo_path / "data").mkdir()
        (demo_path / "data" / "lakehouse").mkdir()
        (demo_path / "bindings").mkdir()
        (demo_path / "ontology" / "test.ttl").write_text("# Test")

        # Create entity CSVs
        (demo_path / "data" / "lakehouse" / "DimCustomer.csv").write_text(
            "CustomerId,Name\nC001,Alice\nC002,Bob\n"
        )
        (demo_path / "data" / "lakehouse" / "DimOrder.csv").write_text(
            "OrderId,CustomerId,Total\nO001,C001,100\nO002,C002,200\n"
        )

        # Create bindings.yaml with WRONG sourceKeyColumn name
        bindings_yaml = """
_schema_version: "1.0"

lakehouse:
  entities:
    - entity: Customer
      sourceTable: DimCustomer
      keyColumn: CustomerId
      properties:
        - property: CustomerId
          column: CustomerId
          type: string
        - property: Name
          column: Name
          type: string
    - entity: SalesOrder
      sourceTable: DimOrder
      keyColumn: OrderId
      properties:
        - property: OrderId
          column: OrderId
          type: string
        - property: Total
          column: Total
          type: double

  relationships:
    - relationship: PLACED
      sourceEntity: Customer
      targetEntity: SalesOrder
      sourceTable: DimOrder
      sourceKeyColumn: CustomerKey  # WRONG - should be CustomerId
      targetKeyColumn: OrderId
"""
        (demo_path / "bindings" / "bindings.yaml").write_text(bindings_yaml)

        result = validate_demo_package(demo_path)

        # Should have error about sourceKeyColumn mismatch
        assert any(
            "sourceKeyColumn" in str(i) and "does NOT match" in str(i)
            for i in result.issues
        )

    def test_validate_relationship_correct_keys(self, tmp_path):
        """Test that correct key column names pass validation."""
        demo_path = tmp_path / "TestDemo"
        demo_path.mkdir()
        (demo_path / "ontology").mkdir()
        (demo_path / "data").mkdir()
        (demo_path / "data" / "lakehouse").mkdir()
        (demo_path / "bindings").mkdir()
        (demo_path / "ontology" / "test.ttl").write_text("# Test")

        # Create entity CSVs
        (demo_path / "data" / "lakehouse" / "DimCustomer.csv").write_text(
            "CustomerId,Name\nC001,Alice\nC002,Bob\n"
        )
        (demo_path / "data" / "lakehouse" / "DimOrder.csv").write_text(
            "OrderId,CustomerId,Total\nO001,C001,100\nO002,C002,200\n"
        )

        # Create bindings.yaml with CORRECT key column names
        bindings_yaml = """
_schema_version: "1.0"

lakehouse:
  entities:
    - entity: Customer
      sourceTable: DimCustomer
      keyColumn: CustomerId
      properties:
        - property: CustomerId
          column: CustomerId
          type: string
        - property: Name
          column: Name
          type: string
    - entity: SalesOrder
      sourceTable: DimOrder
      keyColumn: OrderId
      properties:
        - property: OrderId
          column: OrderId
          type: string
        - property: Total
          column: Total
          type: double

  relationships:
    - relationship: PLACED
      sourceEntity: Customer
      targetEntity: SalesOrder
      sourceTable: DimOrder
      sourceKeyColumn: CustomerId
      targetKeyColumn: OrderId
"""
        (demo_path / "bindings" / "bindings.yaml").write_text(bindings_yaml)

        result = validate_demo_package(demo_path)

        # Should have no errors about key column mismatches
        assert not any(
            "does NOT match" in str(i)
            for i in result.issues
            if i.severity.value == "error"
        )


class TestStaticBindingConstraint:
    """Tests for the single static binding per entity constraint."""

    def test_validate_multiple_static_bindings_error(self, tmp_path):
        """Test that multiple static bindings for same entity raises error."""
        demo_path = tmp_path / "TestDemo"
        demo_path.mkdir()
        (demo_path / "ontology").mkdir()
        (demo_path / "data").mkdir()
        (demo_path / "data" / "lakehouse").mkdir()
        (demo_path / "bindings").mkdir()
        (demo_path / "ontology" / "test.ttl").write_text("# Test")

        # Create CSV files
        (demo_path / "data" / "lakehouse" / "DimProduct.csv").write_text(
            "ProductId,Name\nP001,Widget\n"
        )
        (demo_path / "data" / "lakehouse" / "FactProduct.csv").write_text(
            "ProductId,Sales\nP001,100\n"
        )

        # Create bindings.yaml with duplicate static bindings for same entity
        bindings_yaml = """
_schema_version: "1.0"

lakehouse:
  entities:
    - entity: Product
      sourceTable: DimProduct
      keyColumn: ProductId
      properties:
        - property: ProductId
          column: ProductId
          type: string
        - property: Name
          column: Name
          type: string
    - entity: Product
      sourceTable: FactProduct
      keyColumn: ProductId
      properties:
        - property: Sales
          column: Sales
          type: double
"""
        (demo_path / "bindings" / "bindings.yaml").write_text(bindings_yaml)

        result = validate_demo_package(demo_path)

        # Should have error about multiple static bindings
        assert any(
            "static binding" in str(i).lower()
            for i in result.issues
            if i.severity.value == "error"
        )


class TestTimeseriesAnnotation:
    """Tests for timeseries annotation validation in TTL."""

    def test_validate_timeseries_annotation_present(self, tmp_path):
        """Test that timeseries annotations are detected."""
        demo_path = tmp_path / "TestDemo"
        demo_path.mkdir()
        (demo_path / "ontology").mkdir()
        (demo_path / "data").mkdir()
        (demo_path / "data" / "lakehouse").mkdir()
        (demo_path / "data" / "eventhouse").mkdir()
        (demo_path / "data" / "lakehouse" / "test.csv").write_text("ID\n1\n")
        (demo_path / "data" / "eventhouse" / "telemetry.csv").write_text(
            "Timestamp,ID,Temperature\n2024-01-01T00:00:00Z,1,72.5\n"
        )

        # Create TTL with timeseries annotation
        ttl_content = """
        @prefix : <http://example.com/test#> .
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

        :Temperature a owl:DatatypeProperty ;
            rdfs:label "Temperature" ;
            rdfs:comment "Current temperature reading (timeseries)" ;
            rdfs:range xsd:double .
        """
        (demo_path / "ontology" / "test.ttl").write_text(ttl_content)

        result = validate_demo_package(demo_path)

        # Should have info about timeseries properties found
        assert any(
            "timeseries-annotated" in str(i).lower()
            for i in result.issues
            if i.severity.value == "info"
        )

    def test_validate_missing_timeseries_annotation_warning(self, tmp_path):
        """Test that missing timeseries annotations with eventhouse data warns."""
        demo_path = tmp_path / "TestDemo"
        demo_path.mkdir()
        (demo_path / "ontology").mkdir()
        (demo_path / "data").mkdir()
        (demo_path / "data" / "lakehouse").mkdir()
        (demo_path / "data" / "eventhouse").mkdir()
        (demo_path / "data" / "lakehouse" / "test.csv").write_text("ID\n1\n")
        (demo_path / "data" / "eventhouse" / "telemetry.csv").write_text(
            "Timestamp,ID,Temperature\n2024-01-01T00:00:00Z,1,72.5\n"
        )

        # Create TTL WITHOUT timeseries annotation but with telemetry-like property
        ttl_content = """
        @prefix : <http://example.com/test#> .
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

        :Temperature a owl:DatatypeProperty ;
            rdfs:label "Temperature" ;
            rdfs:range xsd:double .
        """
        (demo_path / "ontology" / "test.ttl").write_text(ttl_content)

        result = validate_demo_package(demo_path)

        # Should have warning about missing timeseries annotation
        assert any(
            "timeseries" in str(i).lower() and "annotation" in str(i).lower()
            for i in result.issues
            if i.severity.value == "warning"
        )
