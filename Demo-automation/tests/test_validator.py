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
