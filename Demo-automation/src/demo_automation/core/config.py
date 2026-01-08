"""
Configuration management for demo automation.

Supports YAML configuration files with environment variable interpolation
and auto-discovery from demo folder structure.
"""

import os
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any

import yaml
from dotenv import load_dotenv

from .errors import ConfigurationError


class ExistingResourceAction(Enum):
    """Action to take when a resource already exists."""
    SKIP = "skip"           # Skip creation, use existing resource
    FAIL = "fail"           # Raise an error
    PROMPT = "prompt"       # Ask user interactively (Y/N)
    RECREATE = "recreate"   # Delete and recreate (cleanup first)


# Load .env file if present
load_dotenv()


def _interpolate_env_vars(value: str) -> str:
    """Replace ${VAR} or $VAR patterns with environment variable values."""
    if not isinstance(value, str):
        return value

    pattern = r"\$\{([^}]+)\}|\$([A-Z_][A-Z0-9_]*)"

    def replace(match):
        var_name = match.group(1) or match.group(2)
        env_value = os.environ.get(var_name)
        if env_value is None:
            raise ConfigurationError(
                f"Environment variable '{var_name}' is not set",
                details={"variable": var_name},
            )
        return env_value

    return re.sub(pattern, replace, value)


def _interpolate_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively interpolate environment variables in a dictionary."""
    result = {}
    for key, value in d.items():
        if isinstance(value, dict):
            result[key] = _interpolate_dict(value)
        elif isinstance(value, list):
            result[key] = [
                _interpolate_dict(v) if isinstance(v, dict) else _interpolate_env_vars(v)
                for v in value
            ]
        elif isinstance(value, str):
            result[key] = _interpolate_env_vars(value)
        else:
            result[key] = value
    return result


@dataclass
class FabricConfig:
    """Fabric workspace configuration."""

    workspace_id: str
    tenant_id: Optional[str] = None
    use_interactive_auth: bool = True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FabricConfig":
        return cls(
            workspace_id=data.get("workspace_id", ""),
            tenant_id=data.get("tenant_id"),
            use_interactive_auth=data.get("use_interactive_auth", True),
        )


@dataclass
class ResourceConfig:
    """Configuration for a single Fabric resource."""

    name: Optional[str] = None
    description: str = ""
    enabled: bool = True
    minimum_consumption_units: float = 0


@dataclass
class ResourcesConfig:
    """Configuration for all Fabric resources."""

    lakehouse: ResourceConfig = field(default_factory=ResourceConfig)
    eventhouse: ResourceConfig = field(default_factory=ResourceConfig)
    ontology: ResourceConfig = field(default_factory=ResourceConfig)

    @classmethod
    def from_dict(cls, data: Dict[str, Any], demo_name: str) -> "ResourcesConfig":
        """Create ResourcesConfig from dict with auto-naming fallback."""
        lakehouse_data = data.get("lakehouse", {})
        eventhouse_data = data.get("eventhouse", {})
        ontology_data = data.get("ontology", {})

        # Fabric doesn't allow hyphens in resource names - use underscores
        safe_name = demo_name.replace("-", "_")

        return cls(
            lakehouse=ResourceConfig(
                name=lakehouse_data.get("name", f"{safe_name}_Lakehouse"),
                description=lakehouse_data.get("description", ""),
                enabled=lakehouse_data.get("enabled", True),
            ),
            eventhouse=ResourceConfig(
                name=eventhouse_data.get("name", f"{safe_name}_Telemetry"),
                description=eventhouse_data.get("description", ""),
                enabled=eventhouse_data.get("enabled", True),
            ),
            ontology=ResourceConfig(
                name=ontology_data.get("name", f"{safe_name}_Ontology"),
                description=ontology_data.get("description", ""),
                enabled=ontology_data.get("enabled", True),
            ),
        )


@dataclass
class BindingOverride:
    """Manual binding override configuration."""

    entity_id: str
    table_name: str
    key_column: str
    timestamp_column: Optional[str] = None
    property_mappings: Dict[str, str] = field(default_factory=dict)


@dataclass
class BindingsConfig:
    """Bindings configuration with auto-discovery support."""

    mode: str = "auto"  # "auto" or "explicit"
    static: List[BindingOverride] = field(default_factory=list)
    timeseries: List[BindingOverride] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BindingsConfig":
        return cls(
            mode=data.get("mode", "auto"),
            static=[
                BindingOverride(**b) for b in data.get("static", [])
            ],
            timeseries=[
                BindingOverride(**b) for b in data.get("timeseries", [])
            ],
        )


@dataclass
class DemoOptions:
    """Demo setup options."""

    skip_existing: bool = True
    interactive: bool = False  # Prompt user Y/N when resources exist
    existing_action: ExistingResourceAction = ExistingResourceAction.SKIP
    validate_before_setup: bool = True
    dry_run: bool = False
    max_parallel_uploads: int = 4
    timeout_seconds: int = 600
    verbose: bool = False

    def get_existing_action(self) -> ExistingResourceAction:
        """Get the action to take when a resource exists."""
        if self.interactive:
            return ExistingResourceAction.PROMPT
        elif self.skip_existing:
            return ExistingResourceAction.SKIP
        else:
            return ExistingResourceAction.FAIL


@dataclass
class LoggingConfig:
    """Logging configuration."""

    level: str = "INFO"
    file: Optional[str] = None
    console: bool = True


@dataclass
class DemoConfiguration:
    """Complete demo configuration."""

    # Demo metadata
    name: str
    demo_path: Path
    description: str = ""
    version: str = "1.0"

    # Fabric settings
    fabric: FabricConfig = field(default_factory=lambda: FabricConfig(workspace_id=""))

    # Resource configuration
    resources: ResourcesConfig = field(default_factory=ResourcesConfig)

    # Bindings configuration
    bindings: BindingsConfig = field(default_factory=BindingsConfig)

    # Options
    options: DemoOptions = field(default_factory=DemoOptions)

    # Logging
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    # Auto-discovered paths
    ontology_file: Optional[Path] = None
    lakehouse_data_path: Optional[Path] = None
    eventhouse_data_path: Optional[Path] = None
    bindings_path: Optional[Path] = None

    @classmethod
    def from_demo_folder(
        cls,
        demo_path: Path,
        workspace_id: Optional[str] = None,
        config_overrides: Optional[Dict[str, Any]] = None,
    ) -> "DemoConfiguration":
        """
        Load configuration from a demo folder with auto-discovery.

        Args:
            demo_path: Path to the demo folder
            workspace_id: Override workspace ID
            config_overrides: Additional configuration overrides

        Returns:
            DemoConfiguration instance
        """
        demo_path = Path(demo_path).resolve()

        if not demo_path.is_dir():
            raise ConfigurationError(
                f"Demo path does not exist or is not a directory: {demo_path}"
            )

        # Load YAML config if present
        config_file = demo_path / "demo.yaml"
        raw_config = {}
        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                raw_config = yaml.safe_load(f) or {}

        # Interpolate environment variables
        try:
            config = _interpolate_dict(raw_config)
        except ConfigurationError:
            # If env var interpolation fails without workspace_id override, re-raise
            if not workspace_id:
                raise
            config = raw_config  # Use raw config, we'll override workspace_id

        # Apply overrides
        if config_overrides:
            config = _merge_dicts(config, config_overrides)

        # Extract sections
        demo_config = config.get("demo", {})
        fabric_config = config.get("fabric", {})
        resources_config = config.get("resources", {})
        bindings_config = config.get("bindings", {})
        options_config = config.get("options", {})
        logging_config = config.get("logging", {})

        # Determine demo name
        name = demo_config.get("name", demo_path.name)

        # Override workspace_id if provided
        if workspace_id:
            fabric_config["workspace_id"] = workspace_id

        # Validate workspace_id
        final_workspace_id = fabric_config.get("workspace_id", "")
        if not final_workspace_id:
            # Try environment variable
            final_workspace_id = os.environ.get("FABRIC_WORKSPACE_ID", "")
        if not final_workspace_id:
            # Try global config file
            from .global_config import GlobalConfig
            global_config = GlobalConfig.load()
            if global_config.workspace_id:
                final_workspace_id = global_config.workspace_id
        fabric_config["workspace_id"] = final_workspace_id

        # Auto-discover paths
        ontology_file = cls._discover_ontology_file(demo_path)
        lakehouse_data_path = cls._discover_data_path(demo_path, "lakehouse")
        eventhouse_data_path = cls._discover_data_path(demo_path, "eventhouse")
        bindings_path = DemoConfiguration._find_folder_case_insensitive(demo_path, "bindings")

        return cls(
            name=name,
            demo_path=demo_path,
            description=demo_config.get("description", ""),
            version=demo_config.get("version", "1.0"),
            fabric=FabricConfig.from_dict(fabric_config),
            resources=ResourcesConfig.from_dict(resources_config, name),
            bindings=BindingsConfig.from_dict(bindings_config),
            options=DemoOptions(
                skip_existing=options_config.get("skip_existing", True),
                validate_before_setup=options_config.get("validate_before_setup", True),
                dry_run=options_config.get("dry_run", False),
                max_parallel_uploads=options_config.get("max_parallel_uploads", 4),
                timeout_seconds=options_config.get("timeout_seconds", 600),
                verbose=options_config.get("verbose", False),
            ),
            logging=LoggingConfig(
                level=logging_config.get("level", "INFO"),
                file=logging_config.get("file"),
                console=logging_config.get("console", True),
            ),
            ontology_file=ontology_file,
            lakehouse_data_path=lakehouse_data_path,
            eventhouse_data_path=eventhouse_data_path,
            bindings_path=bindings_path,
        )

    @staticmethod
    def _find_folder_case_insensitive(parent: Path, folder_name: str) -> Optional[Path]:
        """Find a folder with case-insensitive matching.
        
        Supports both uppercase (.agentic output) and lowercase folder names.
        """
        # Try exact match first
        exact = parent / folder_name
        if exact.is_dir():
            return exact
        
        # Try case variations
        for variant in [folder_name.lower(), folder_name.capitalize(), folder_name.upper()]:
            path = parent / variant
            if path.is_dir():
                return path
        
        # Scan directory for case-insensitive match
        if parent.is_dir():
            for item in parent.iterdir():
                if item.is_dir() and item.name.lower() == folder_name.lower():
                    return item
        return None

    @staticmethod
    def _discover_ontology_file(demo_path: Path) -> Optional[Path]:
        """Find the ontology TTL file in the demo folder."""
        # Try case-insensitive folder discovery
        ontology_dir = DemoConfiguration._find_folder_case_insensitive(demo_path, "ontology")
        if ontology_dir and ontology_dir.is_dir():
            ttl_files = list(ontology_dir.glob("*.ttl"))
            if ttl_files:
                return ttl_files[0]  # Return first TTL file found
        return None

    @staticmethod
    def _discover_data_path(demo_path: Path, data_type: str) -> Optional[Path]:
        """Find the data folder for lakehouse or eventhouse."""
        # Try case-insensitive folder discovery for both 'data' and data_type
        data_dir = DemoConfiguration._find_folder_case_insensitive(demo_path, "data")
        if data_dir:
            type_dir = DemoConfiguration._find_folder_case_insensitive(data_dir, data_type)
            if type_dir and type_dir.is_dir():
                return type_dir
        return None

    def get_lakehouse_csv_files(self) -> List[Path]:
        """Get list of CSV files for lakehouse tables."""
        if self.lakehouse_data_path and self.lakehouse_data_path.is_dir():
            return list(self.lakehouse_data_path.glob("*.csv"))
        return []

    def get_eventhouse_csv_files(self) -> List[Path]:
        """Get list of CSV files for eventhouse tables."""
        if self.eventhouse_data_path and self.eventhouse_data_path.is_dir():
            return list(self.eventhouse_data_path.glob("*.csv"))
        return []

    def validate(self) -> List[str]:
        """
        Validate the configuration.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Check workspace_id
        if not self.fabric.workspace_id:
            errors.append(
                "workspace_id is required. Set FABRIC_WORKSPACE_ID environment variable "
                "or specify in demo.yaml or via --workspace-id"
            )

        # Check ontology file
        if self.ontology_file and not self.ontology_file.exists():
            errors.append(f"Ontology file not found: {self.ontology_file}")

        # Check data paths
        lakehouse_files = self.get_lakehouse_csv_files()
        eventhouse_files = self.get_eventhouse_csv_files()

        if not lakehouse_files and not eventhouse_files:
            errors.append(
                "No data files found. Expected CSV files in data/lakehouse/ or data/eventhouse/"
            )

        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "demo": {
                "name": self.name,
                "description": self.description,
                "version": self.version,
            },
            "fabric": {
                "workspace_id": self.fabric.workspace_id,
                "tenant_id": self.fabric.tenant_id,
            },
            "resources": {
                "lakehouse": {"name": self.resources.lakehouse.name},
                "eventhouse": {"name": self.resources.eventhouse.name},
                "ontology": {"name": self.resources.ontology.name},
            },
            "options": {
                "skip_existing": self.options.skip_existing,
                "dry_run": self.options.dry_run,
            },
            "paths": {
                "demo_path": str(self.demo_path),
                "ontology_file": str(self.ontology_file) if self.ontology_file else None,
                "lakehouse_data": str(self.lakehouse_data_path) if self.lakehouse_data_path else None,
                "eventhouse_data": str(self.eventhouse_data_path) if self.eventhouse_data_path else None,
            },
        }


def _merge_dicts(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _merge_dicts(result[key], value)
        else:
            result[key] = value
    return result


def generate_demo_yaml_template(demo_path: Path) -> str:
    """Generate a demo.yaml template for a demo folder."""
    demo_name = demo_path.name

    return f"""# Demo configuration for {demo_name}
# Generated by fabric-demo init

demo:
  name: {demo_name}
  # description: "Your demo description"
  # version: "1.0"

fabric:
  workspace_id: ${{FABRIC_WORKSPACE_ID}}
  # tenant_id: ${{AZURE_TENANT_ID}}

# Optional: Override auto-discovered resource names
# resources:
#   lakehouse:
#     name: {demo_name}-Lakehouse
#   eventhouse:
#     name: {demo_name}-Telemetry
#   ontology:
#     name: {demo_name}-Ontology

# Optional: Override auto-discovered bindings
# bindings:
#   mode: auto  # or "explicit"

options:
  skip_existing: true
  validate_before_setup: true
  dry_run: false

logging:
  level: INFO
  console: true
"""
