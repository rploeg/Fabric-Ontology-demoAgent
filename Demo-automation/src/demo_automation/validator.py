"""
Demo Package Validator.

Validates that a demo package matches the expected structure from the
fabric-ontology-demo-v2.yaml generator spec.

Supports two binding formats:
1. bindings/bindings.yaml (preferred - machine-readable, spec v3.2+)
2. bindings/*.md (legacy fallback - requires markdown parsing)
"""

import csv
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Set, Dict, Any
from enum import Enum

import yaml

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Severity level for validation issues."""
    ERROR = "error"      # Must fix before setup
    WARNING = "warning"  # Should fix but can proceed
    INFO = "info"        # Best practice suggestion


@dataclass
class ValidationIssue:
    """A validation issue found in the demo package."""
    severity: ValidationSeverity
    message: str
    path: Optional[str] = None
    suggestion: Optional[str] = None

    def __str__(self) -> str:
        prefix = {
            ValidationSeverity.ERROR: "ERROR",
            ValidationSeverity.WARNING: "WARNING",
            ValidationSeverity.INFO: "INFO",
        }[self.severity]

        msg = f"[{prefix}] {self.message}"
        if self.path:
            msg += f" ({self.path})"
        if self.suggestion:
            msg += f"\n         → {self.suggestion}"
        return msg


@dataclass
class ValidationResult:
    """Result of demo package validation."""
    demo_path: Path
    issues: List[ValidationIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Check if the package is valid (no errors)."""
        return not any(i.severity == ValidationSeverity.ERROR for i in self.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == ValidationSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == ValidationSeverity.WARNING)

    @property
    def info_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == ValidationSeverity.INFO)

    def add_error(self, message: str, path: str = None, suggestion: str = None) -> None:
        self.issues.append(ValidationIssue(
            severity=ValidationSeverity.ERROR,
            message=message,
            path=path,
            suggestion=suggestion,
        ))

    def add_warning(self, message: str, path: str = None, suggestion: str = None) -> None:
        self.issues.append(ValidationIssue(
            severity=ValidationSeverity.WARNING,
            message=message,
            path=path,
            suggestion=suggestion,
        ))

    def add_info(self, message: str, path: str = None, suggestion: str = None) -> None:
        self.issues.append(ValidationIssue(
            severity=ValidationSeverity.INFO,
            message=message,
            path=path,
            suggestion=suggestion,
        ))


class DemoPackageValidator:
    """
    Validates demo package structure and content.

    Expected structure (from fabric-ontology-demo-v2.yaml):
    ```
    {DemoName}/
    ├── .demo-metadata.yaml           (optional, v3.1+)
    ├── demo.yaml                     (optional)
    ├── ontology/
    │   ├── *.ttl                     (required)
    │   └── ontology-structure.md
    ├── data/
    │   ├── lakehouse/*.csv           (at least one)
    │   └── eventhouse/*.csv          (optional)
    ├── bindings/
    │   ├── lakehouse-binding.md
    │   └── eventhouse-binding.md
    ├── queries/
    │   └── demo-questions.md
    └── README.md
    ```
    """

    # Required directories
    REQUIRED_DIRS = ["ontology", "data"]

    # Expected files
    EXPECTED_FILES = ["README.md"]

    # Valid entity key data types
    VALID_KEY_TYPES = {"string", "str", "int", "integer", "long"}

    def __init__(self, demo_path: Path):
        """
        Initialize validator.

        Args:
            demo_path: Path to the demo folder
        """
        self.demo_path = Path(demo_path).resolve()
        self.result = ValidationResult(demo_path=self.demo_path)

    def validate(self) -> ValidationResult:
        """
        Run all validation checks.

        Returns:
            ValidationResult with all issues found
        """
        logger.info(f"Validating demo package: {self.demo_path}")

        # Basic structure checks
        self._check_directory_exists()
        if not self.demo_path.is_dir():
            return self.result

        self._check_required_directories()
        self._check_expected_files()

        # Data checks
        self._check_ontology_files()
        self._check_data_files()
        self._check_csv_structure()

        # Binding checks
        self._check_bindings()

        # Metadata checks
        self._check_metadata()

        logger.info(
            f"Validation complete: {self.result.error_count} errors, "
            f"{self.result.warning_count} warnings"
        )

        return self.result

    def _check_directory_exists(self) -> None:
        """Check if demo directory exists."""
        if not self.demo_path.exists():
            self.result.add_error(
                f"Demo path does not exist",
                path=str(self.demo_path),
            )
        elif not self.demo_path.is_dir():
            self.result.add_error(
                f"Demo path is not a directory",
                path=str(self.demo_path),
            )

    def _check_required_directories(self) -> None:
        """Check for required directories."""
        for dir_name in self.REQUIRED_DIRS:
            dir_path = self.demo_path / dir_name
            if not dir_path.is_dir():
                self.result.add_error(
                    f"Required directory missing: {dir_name}/",
                    suggestion=f"Create {dir_path}",
                )

    def _check_expected_files(self) -> None:
        """Check for expected files."""
        for file_name in self.EXPECTED_FILES:
            file_path = self.demo_path / file_name
            if not file_path.exists():
                self.result.add_warning(
                    f"Expected file missing: {file_name}",
                    suggestion=f"Create {file_path}",
                )

    def _check_ontology_files(self) -> None:
        """Check ontology directory and files."""
        # Case-insensitive folder discovery for ontology/ or Ontology/
        ontology_dir = None
        for variant in ["ontology", "Ontology"]:
            candidate = self.demo_path / variant
            if candidate.is_dir():
                ontology_dir = candidate
                break
        
        if not ontology_dir:
            return

        # Check for TTL files
        ttl_files = list(ontology_dir.glob("*.ttl"))
        if not ttl_files:
            self.result.add_error(
                "No TTL ontology file found",
                path="ontology/",
                suggestion="Add a .ttl file with the ontology definition",
            )
        elif len(ttl_files) > 1:
            self.result.add_warning(
                f"Multiple TTL files found ({len(ttl_files)}), first one will be used",
                path="ontology/",
            )

        # Check for structure documentation
        structure_md = ontology_dir / "ontology-structure.md"
        if not structure_md.exists():
            self.result.add_info(
                "ontology-structure.md not found",
                suggestion="Consider adding documentation for the ontology structure",
            )

    def _check_data_files(self) -> None:
        """Check data directory structure and files."""
        # Case-insensitive folder discovery for data/ or Data/
        data_dir = None
        for variant in ["data", "Data"]:
            candidate = self.demo_path / variant
            if candidate.is_dir():
                data_dir = candidate
                break
        
        if not data_dir:
            return

        # Case-insensitive lakehouse folder discovery
        lakehouse_dir = None
        for variant in ["lakehouse", "Lakehouse"]:
            candidate = data_dir / variant
            if candidate.is_dir():
                lakehouse_dir = candidate
                break
        
        if lakehouse_dir:
            csv_files = list(lakehouse_dir.glob("*.csv"))
            if not csv_files:
                self.result.add_warning(
                    "No CSV files found in data/lakehouse/",
                    suggestion="Add CSV files for static data tables",
                )
            else:
                self.result.add_info(
                    f"Found {len(csv_files)} lakehouse CSV files",
                )
        else:
            self.result.add_warning(
                "data/lakehouse/ directory not found",
                suggestion="Create directory for static data CSV files",
            )

        # Case-insensitive eventhouse folder discovery
        eventhouse_dir = None
        for variant in ["eventhouse", "Eventhouse"]:
            candidate = data_dir / variant
            if candidate.is_dir():
                eventhouse_dir = candidate
                break
        
        if eventhouse_dir:
            csv_files = list(eventhouse_dir.glob("*.csv"))
            if csv_files:
                self.result.add_info(
                    f"Found {len(csv_files)} eventhouse CSV files",
                )
        else:
            self.result.add_info(
                "data/eventhouse/ directory not found (optional)",
            )

    def _check_csv_structure(self) -> None:
        """Validate CSV file structure."""
        data_dir = self.demo_path / "data"
        if not data_dir.is_dir():
            return

        # Check all CSV files
        for csv_file in data_dir.rglob("*.csv"):
            self._validate_csv_file(csv_file)

    def _validate_csv_file(self, csv_path: Path) -> None:
        """Validate a single CSV file."""
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                headers = next(reader, None)

                if not headers:
                    self.result.add_error(
                        f"CSV file is empty or has no headers",
                        path=str(csv_path.relative_to(self.demo_path)),
                    )
                    return

                # Check for empty headers
                empty_headers = [i for i, h in enumerate(headers) if not h.strip()]
                if empty_headers:
                    self.result.add_warning(
                        f"CSV has empty column headers at positions: {empty_headers}",
                        path=str(csv_path.relative_to(self.demo_path)),
                    )

                # Check for ID column (common convention)
                has_id_column = any(
                    "id" in h.lower() for h in headers
                )
                if not has_id_column:
                    self.result.add_info(
                        f"CSV has no obvious ID column",
                        path=str(csv_path.relative_to(self.demo_path)),
                        suggestion="Consider having a column ending with 'ID' for entity keys",
                    )

                # Count rows (sample)
                row_count = sum(1 for _ in reader)
                if row_count == 0:
                    self.result.add_warning(
                        f"CSV has no data rows",
                        path=str(csv_path.relative_to(self.demo_path)),
                    )

        except Exception as e:
            self.result.add_error(
                f"Failed to parse CSV: {e}",
                path=str(csv_path.relative_to(self.demo_path)),
            )

    def _check_bindings(self) -> None:
        """Check binding configuration - prefer YAML, fallback to markdown."""
        # Case-insensitive folder discovery for bindings/ or Bindings/
        bindings_dir = None
        for variant in ["bindings", "Bindings"]:
            candidate = self.demo_path / variant
            if candidate.is_dir():
                bindings_dir = candidate
                break
        
        # Fallback: scan directory for case-insensitive match
        if bindings_dir is None and self.demo_path.is_dir():
            for item in self.demo_path.iterdir():
                if item.is_dir() and item.name.lower() == "bindings":
                    bindings_dir = item
                    break
        
        if not bindings_dir:
            self.result.add_warning(
                "bindings/ directory not found",
                suggestion="Create Bindings/ with bindings.yaml (preferred) or markdown files",
            )
            return

        # Prefer bindings.yaml (v3.2+ format)
        bindings_yaml = bindings_dir / "bindings.yaml"
        if bindings_yaml.exists():
            self.result.add_info("Found bindings.yaml (v3.2+ format - preferred)")
            self._validate_bindings_yaml(bindings_yaml)
            return

        # Fallback to markdown binding files (legacy)
        self._validate_bindings_markdown_legacy(bindings_dir)

    def _validate_bindings_yaml(self, bindings_yaml: Path) -> None:
        """Validate YAML binding configuration against CSV data."""
        try:
            with open(bindings_yaml, "r", encoding="utf-8") as f:
                bindings_data = yaml.safe_load(f)
            
            if not bindings_data:
                self.result.add_error(
                    "bindings.yaml is empty",
                    path="bindings/bindings.yaml",
                )
                return
            
            # Validate version - support both 'version' and '_schema_version'
            version = bindings_data.get("version") or bindings_data.get("_schema_version")
            if not version:
                self.result.add_warning(
                    "bindings.yaml missing 'version' or '_schema_version' field",
                    suggestion="Add '_schema_version: \"1.0\"' to bindings.yaml",
                )
            
            # Load CSV headers for cross-validation
            csv_headers = self._load_csv_headers()
            
            # Validate lakehouse bindings
            lakehouse = bindings_data.get("lakehouse", {})
            if lakehouse:
                self._validate_yaml_source_bindings(
                    lakehouse, "lakehouse", csv_headers.get("lakehouse", {})
                )
            
            # Validate eventhouse bindings
            eventhouse = bindings_data.get("eventhouse", {})
            if eventhouse:
                self._validate_yaml_source_bindings(
                    eventhouse, "eventhouse", csv_headers.get("eventhouse", {})
                )
            
            if not lakehouse and not eventhouse:
                self.result.add_warning(
                    "bindings.yaml has no lakehouse or eventhouse bindings",
                    suggestion="Add 'lakehouse' or 'eventhouse' section with entity bindings",
                )
                
        except yaml.YAMLError as e:
            self.result.add_error(
                f"Invalid YAML in bindings.yaml: {e}",
                path="bindings/bindings.yaml",
            )
        except Exception as e:
            self.result.add_error(
                f"Failed to read bindings.yaml: {e}",
                path="bindings/bindings.yaml",
            )

    def _validate_yaml_source_bindings(
        self,
        source_data: dict,
        source_type: str,
        csv_headers: Dict[str, Set[str]],
    ) -> None:
        """Validate entity and relationship bindings from YAML against CSV."""
        entities = source_data.get("entities", [])
        relationships = source_data.get("relationships", [])
        
        self.result.add_info(
            f"Found {len(entities)} entity bindings and {len(relationships)} "
            f"relationship bindings for {source_type}"
        )
        
        for entity in entities:
            self._validate_yaml_entity(entity, source_type, csv_headers)
        
        for relationship in relationships:
            self._validate_yaml_relationship(relationship, source_type, csv_headers)

    def _validate_yaml_entity(
        self,
        entity: dict,
        source_type: str,
        csv_headers: Dict[str, Set[str]],
    ) -> None:
        """Validate a single entity binding from YAML."""
        entity_name = entity.get("entity")
        table_name = entity.get("sourceTable")
        
        if not entity_name:
            self.result.add_error(
                f"Entity binding missing 'entity' field in {source_type}",
            )
            return
        
        if not table_name:
            self.result.add_error(
                f"Entity '{entity_name}' missing 'sourceTable' field",
                suggestion="Add 'sourceTable: TableName' to the entity binding",
            )
            return
        
        if table_name not in csv_headers:
            self.result.add_error(
                f"Entity '{entity_name}' references table '{table_name}' "
                f"which does not exist in data/{source_type}/",
                suggestion=f"Create {table_name}.csv or correct the table name",
            )
            return
        
        available_columns = csv_headers[table_name]
        
        # Check key column
        key_column = entity.get("keyColumn")
        if key_column and key_column not in available_columns:
            self.result.add_error(
                f"Entity '{entity_name}' key column '{key_column}' "
                f"not found in {table_name}.csv",
                suggestion=f"Available columns: {', '.join(sorted(available_columns)[:10])}",
            )
        
        # Check timestamp column (for timeseries)
        timestamp_col = entity.get("timestampColumn")
        if timestamp_col and timestamp_col not in available_columns:
            self.result.add_error(
                f"Entity '{entity_name}' timestamp column '{timestamp_col}' "
                f"not found in {table_name}.csv",
            )
        
        # Validate property mappings
        properties = entity.get("properties", [])
        for prop in properties:
            source_col = prop.get("column")
            target_prop = prop.get("property")
            if source_col and source_col not in available_columns:
                self.result.add_warning(
                    f"Entity '{entity_name}' property '{target_prop}' "
                    f"maps to column '{source_col}' which doesn't exist",
                    suggestion=f"Check column name in {table_name}.csv",
                )

    def _validate_yaml_relationship(
        self,
        relationship: dict,
        source_type: str,
        csv_headers: Dict[str, Set[str]],
    ) -> None:
        """Validate a single relationship binding from YAML."""
        rel_name = relationship.get("relationship")
        table_name = relationship.get("sourceTable")
        
        if not rel_name:
            self.result.add_warning(
                f"Relationship binding missing 'relationship' field in {source_type}",
            )
            return
        
        if not table_name:
            self.result.add_warning(
                f"Relationship '{rel_name}' missing 'sourceTable' field",
            )
            return
        
        if table_name not in csv_headers:
            self.result.add_warning(
                f"Relationship '{rel_name}' references table '{table_name}' "
                f"which doesn't exist in data/{source_type}/",
            )
            return
        
        available_columns = csv_headers[table_name]
        
        # Check source key column
        source_key = relationship.get("sourceKeyColumn")
        if source_key and source_key not in available_columns:
            self.result.add_error(
                f"Relationship '{rel_name}' source key column "
                f"'{source_key}' not found in {table_name}.csv",
            )
        
        # Check target key column
        target_key = relationship.get("targetKeyColumn")
        if target_key and target_key not in available_columns:
            self.result.add_error(
                f"Relationship '{rel_name}' target key column "
                f"'{target_key}' not found in {table_name}.csv",
            )

    def _validate_bindings_markdown_legacy(self, bindings_dir: Path) -> None:
        """Validate binding markdown files (legacy format)."""
        lakehouse_binding = bindings_dir / "lakehouse-binding.md"
        eventhouse_binding = bindings_dir / "eventhouse-binding.md"

        if not lakehouse_binding.exists() and not eventhouse_binding.exists():
            self.result.add_warning(
                "No binding configuration files found",
                suggestion="Add bindings.yaml (preferred) or lakehouse-binding.md/eventhouse-binding.md",
            )
            return

        self.result.add_info(
            "Using markdown binding files (consider migrating to bindings.yaml)"
        )

        # Load CSV headers for cross-validation
        csv_headers = self._load_csv_headers()

        if lakehouse_binding.exists():
            self.result.add_info("Found lakehouse-binding.md (legacy format)")
            self._validate_binding_file(
                lakehouse_binding,
                "lakehouse",
                csv_headers.get("lakehouse", {}),
            )

        if eventhouse_binding.exists():
            self.result.add_info("Found eventhouse-binding.md (legacy format)")
            self._validate_binding_file(
                eventhouse_binding,
                "eventhouse",
                csv_headers.get("eventhouse", {}),
            )

    def _load_csv_headers(self) -> Dict[str, Dict[str, Set[str]]]:
        """
        Load CSV headers from data directories.
        
        Returns:
            Dict mapping source type -> table name -> set of column names
        """
        headers = {"lakehouse": {}, "eventhouse": {}}
        data_dir = self.demo_path / "data"
        
        if not data_dir.is_dir():
            return headers
        
        for source_type in ["lakehouse", "eventhouse"]:
            source_dir = data_dir / source_type
            if source_dir.is_dir():
                for csv_file in source_dir.glob("*.csv"):
                    try:
                        with open(csv_file, "r", encoding="utf-8") as f:
                            reader = csv.reader(f)
                            file_headers = next(reader, [])
                            # Store both the original case and lower case for matching
                            headers[source_type][csv_file.stem] = set(file_headers)
                    except Exception as e:
                        logger.warning(f"Failed to read headers from {csv_file}: {e}")
        
        return headers

    def _validate_binding_file(
        self,
        binding_path: Path,
        source_type: str,
        csv_headers: Dict[str, Set[str]],
    ) -> None:
        """
        Validate binding file content against CSV data.
        
        Args:
            binding_path: Path to the binding markdown file
            source_type: 'lakehouse' or 'eventhouse'
            csv_headers: Dict mapping table names to column sets
        """
        try:
            # Import the binding parser - use the parser's BindingType
            from .binding.binding_parser import BindingMarkdownParser, BindingType
            
            binding_type = (
                BindingType.STATIC if source_type == "lakehouse" 
                else BindingType.TIMESERIES
            )
            parser = BindingMarkdownParser(binding_type)
            
            # Parse with relationships if lakehouse
            if source_type == "lakehouse":
                entity_bindings, relationship_bindings = parser.parse_file_with_relationships(
                    binding_path
                )
            else:
                entity_bindings = parser.parse_file(binding_path)
                relationship_bindings = []
            
            if not entity_bindings:
                self.result.add_warning(
                    f"No entity bindings parsed from {binding_path.name}",
                    path=f"bindings/{binding_path.name}",
                    suggestion="Check markdown format matches expected entity binding structure",
                )
                return
            
            self.result.add_info(
                f"Parsed {len(entity_bindings)} entity bindings from {binding_path.name}"
            )
            
            # Validate each entity binding
            for binding in entity_bindings:
                self._validate_entity_binding(binding, source_type, csv_headers)
            
            # Validate relationship bindings
            if relationship_bindings:
                self.result.add_info(
                    f"Parsed {len(relationship_bindings)} relationship bindings from {binding_path.name}"
                )
                for rel_binding in relationship_bindings:
                    self._validate_relationship_binding(rel_binding, csv_headers)
                    
        except ImportError as e:
            self.result.add_warning(
                f"Could not import binding parser: {e}",
                suggestion="Install binding module dependencies",
            )
        except Exception as e:
            self.result.add_error(
                f"Failed to parse binding file: {e}",
                path=f"bindings/{binding_path.name}",
            )

    def _validate_entity_binding(
        self,
        binding,
        source_type: str,
        csv_headers: Dict[str, Set[str]],
    ) -> None:
        """Validate a single entity binding against CSV data."""
        entity_name = binding.entity_name
        table_name = binding.table_name
        
        # Check if table exists
        if not table_name:
            self.result.add_error(
                f"Entity '{entity_name}' has no table name specified",
                suggestion="Add 'Source Table' specification in binding",
            )
            return
        
        if table_name not in csv_headers:
            self.result.add_error(
                f"Entity '{entity_name}' references table '{table_name}' "
                f"which does not exist in data/{source_type}/",
                suggestion=f"Create {table_name}.csv or correct the table name in binding",
            )
            return
        
        available_columns = csv_headers[table_name]
        
        # Check key column exists
        if binding.key_column:
            if binding.key_column not in available_columns:
                self.result.add_error(
                    f"Entity '{entity_name}' key column '{binding.key_column}' "
                    f"not found in {table_name}.csv",
                    suggestion=f"Available columns: {', '.join(sorted(available_columns)[:10])}...",
                )
        else:
            self.result.add_warning(
                f"Entity '{entity_name}' has no key column specified",
                suggestion="Add 'Key Column' specification in binding",
            )
        
        # Check timestamp column for timeseries
        if binding.timestamp_column:
            if binding.timestamp_column not in available_columns:
                self.result.add_error(
                    f"Entity '{entity_name}' timestamp column '{binding.timestamp_column}' "
                    f"not found in {table_name}.csv",
                )
        
        # Validate property mappings
        if binding.property_mappings:
            for mapping in binding.property_mappings:
                if mapping.source_column not in available_columns:
                    self.result.add_warning(
                        f"Entity '{entity_name}' property '{mapping.target_property}' "
                        f"maps to column '{mapping.source_column}' which doesn't exist",
                        suggestion=f"Check column name in {table_name}.csv",
                    )
        else:
            self.result.add_info(
                f"Entity '{entity_name}' has no property mappings defined",
            )

    def _validate_relationship_binding(
        self,
        rel_binding,
        csv_headers: Dict[str, Set[str]],
    ) -> None:
        """Validate a relationship binding against CSV data."""
        rel_name = rel_binding.relationship_name
        table_name = rel_binding.table_name
        
        if not table_name:
            self.result.add_warning(
                f"Relationship '{rel_name}' has no table name specified",
            )
            return
        
        if table_name not in csv_headers:
            self.result.add_warning(
                f"Relationship '{rel_name}' references table '{table_name}' "
                f"which doesn't exist in CSV data",
            )
            return
        
        available_columns = csv_headers[table_name]
        
        # Check source key column
        if rel_binding.source_key_column:
            if rel_binding.source_key_column not in available_columns:
                self.result.add_error(
                    f"Relationship '{rel_name}' source key column "
                    f"'{rel_binding.source_key_column}' not found in {table_name}.csv",
                )
        
        # Check target key column
        if rel_binding.target_key_column:
            if rel_binding.target_key_column not in available_columns:
                self.result.add_error(
                    f"Relationship '{rel_name}' target key column "
                    f"'{rel_binding.target_key_column}' not found in {table_name}.csv",
                )

    def _check_metadata(self) -> None:
        """Check for metadata files."""
        demo_yaml = self.demo_path / "demo.yaml"
        if not demo_yaml.exists():
            self.result.add_info(
                "demo.yaml not found",
                suggestion="Run 'fabric-demo init' to create configuration",
            )

        metadata_yaml = self.demo_path / ".demo-metadata.yaml"
        if metadata_yaml.exists():
            self.result.add_info("Found .demo-metadata.yaml (v3.1+ format)")


def validate_demo_package(demo_path: Path) -> ValidationResult:
    """
    Validate a demo package and return result.

    Args:
        demo_path: Path to the demo folder

    Returns:
        ValidationResult with all issues found
    """
    validator = DemoPackageValidator(demo_path)
    return validator.validate()
