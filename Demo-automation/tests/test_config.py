"""
Tests for configuration module.
"""

import os
import pytest
from pathlib import Path
from unittest.mock import patch

from demo_automation.core.config import (
    DemoConfiguration,
    FabricConfig,
    _interpolate_env_vars,
    generate_demo_yaml_template,
)
from demo_automation.core.errors import ConfigurationError


class TestEnvVarInterpolation:
    """Tests for environment variable interpolation."""

    def test_interpolate_simple_var(self):
        """Test interpolating ${VAR} pattern."""
        with patch.dict(os.environ, {"TEST_VAR": "test_value"}):
            result = _interpolate_env_vars("${TEST_VAR}")
            assert result == "test_value"

    def test_interpolate_embedded_var(self):
        """Test interpolating embedded variable."""
        with patch.dict(os.environ, {"WORKSPACE": "my-workspace"}):
            result = _interpolate_env_vars("prefix-${WORKSPACE}-suffix")
            assert result == "prefix-my-workspace-suffix"

    def test_missing_var_raises_error(self):
        """Test that missing env var raises ConfigurationError."""
        with pytest.raises(ConfigurationError):
            _interpolate_env_vars("${NONEXISTENT_VAR}")

    def test_non_string_passthrough(self):
        """Test that non-strings pass through unchanged."""
        assert _interpolate_env_vars(123) == 123
        assert _interpolate_env_vars(None) is None


class TestFabricConfig:
    """Tests for FabricConfig."""

    def test_from_dict_minimal(self):
        """Test creating config from minimal dict."""
        config = FabricConfig.from_dict({
            "workspace_id": "test-workspace-id"
        })
        assert config.workspace_id == "test-workspace-id"
        assert config.tenant_id is None
        assert config.use_interactive_auth is True

    def test_from_dict_full(self):
        """Test creating config from full dict."""
        config = FabricConfig.from_dict({
            "workspace_id": "test-workspace",
            "tenant_id": "test-tenant",
            "use_interactive_auth": False,
        })
        assert config.workspace_id == "test-workspace"
        assert config.tenant_id == "test-tenant"
        assert config.use_interactive_auth is False


class TestDemoConfiguration:
    """Tests for DemoConfiguration."""

    def test_from_demo_folder_minimal(self, tmp_path):
        """Test loading config from minimal demo folder."""
        # Create minimal structure
        demo_path = tmp_path / "TestDemo"
        demo_path.mkdir()
        (demo_path / "ontology").mkdir()
        (demo_path / "data").mkdir()
        (demo_path / "data" / "lakehouse").mkdir()

        # Create a test CSV
        csv_file = demo_path / "data" / "lakehouse" / "test.csv"
        csv_file.write_text("ID,Name\n1,Test\n")

        # Create TTL file
        ttl_file = demo_path / "ontology" / "test.ttl"
        ttl_file.write_text("# Test ontology")

        with patch.dict(os.environ, {"FABRIC_WORKSPACE_ID": "test-workspace"}):
            config = DemoConfiguration.from_demo_folder(demo_path)

        assert config.name == "TestDemo"
        assert config.fabric.workspace_id == "test-workspace"
        assert config.resources.lakehouse.name == "TestDemo-Lakehouse"

    def test_workspace_id_override(self, tmp_path):
        """Test workspace_id override."""
        demo_path = tmp_path / "TestDemo"
        demo_path.mkdir()
        (demo_path / "ontology").mkdir()
        (demo_path / "data").mkdir()

        config = DemoConfiguration.from_demo_folder(
            demo_path,
            workspace_id="override-workspace",
        )

        assert config.fabric.workspace_id == "override-workspace"

    def test_validate_missing_workspace(self, tmp_path):
        """Test validation fails without workspace_id."""
        demo_path = tmp_path / "TestDemo"
        demo_path.mkdir()
        (demo_path / "ontology").mkdir()
        (demo_path / "data").mkdir()

        config = DemoConfiguration.from_demo_folder(demo_path)
        errors = config.validate()

        assert any("workspace_id" in e for e in errors)


class TestGenerateDemoYamlTemplate:
    """Tests for demo.yaml template generation."""

    def test_template_contains_demo_name(self, tmp_path):
        """Test that template contains demo name."""
        demo_path = tmp_path / "MyDemo"
        demo_path.mkdir()

        template = generate_demo_yaml_template(demo_path)

        assert "MyDemo" in template
        assert "name: MyDemo" in template

    def test_template_has_workspace_placeholder(self, tmp_path):
        """Test that template has workspace_id placeholder."""
        demo_path = tmp_path / "TestDemo"
        demo_path.mkdir()

        template = generate_demo_yaml_template(demo_path)

        assert "${FABRIC_WORKSPACE_ID}" in template
