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
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Set, Dict, Any
from enum import Enum

import yaml

# SDK validation imports - Phase 4 integration
from fabric_ontology.validation import (
    validate_name as sdk_validate_name,
    validate_data_type as sdk_validate_data_type,
    GQL_RESERVED_WORDS as SDK_GQL_RESERVED_WORDS,
    MAX_NAME_LENGTH as SDK_MAX_NAME_LENGTH,
    NAME_PATTERN as SDK_NAME_PATTERN,
    OntologyValidator,
)
from fabric_ontology.exceptions import ValidationError as SDKValidationError

logger = logging.getLogger(__name__)

# SDK's MAX_NAME_LENGTH is the recommended limit (26 chars)
RECOMMENDED_NAME_LENGTH = SDK_MAX_NAME_LENGTH

# GQL Reserved words - now uses SDK's comprehensive list with fallback
# The SDK's GQL_RESERVED_WORDS is more complete and authoritative
GQL_RESERVED_WORDS = SDK_GQL_RESERVED_WORDS

# Valid property/entity name pattern - now uses SDK's authoritative pattern
# SDK pattern: ^[a-zA-Z][a-zA-Z0-9_-]{0,25}$ (must start with letter, 1-26 chars)
NAME_PATTERN = SDK_NAME_PATTERN

# =============================================================================
# Legacy Validation Constants (kept for backwards compatibility)
# Note: Primary validation now uses SDK functions in _validate_name_constraints()
# and _validate_data_type(). These constants are used for demo-specific checks.
# =============================================================================
VALID_PROPERTY_TYPES = {"string", "str", "int", "integer", "long", "double", "float", "boolean", "bool", "datetime"}
VALID_KEY_TYPES = {"string", "str", "int", "integer", "long"}
INVALID_TYPES = {"decimal"}  # Decimal returns NULL in Graph queries


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
    ├── .demo-metadata.yaml           (required, v3.1+)
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
        # Track property names for uniqueness check
        self._all_property_names: Set[str] = set()
        # Track entity keys for relationship validation
        self._entity_keys: Dict[str, str] = {}  # entity_name -> key_column

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

        # Binding checks (also populates _entity_keys and _all_property_names)
        self._check_bindings()

        # Cross-validation checks
        self._check_property_uniqueness()
        self._check_ttl_constraints()

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

        # Check for structure documentation (at root level, not in ontology/)
        structure_md = self.demo_path / "ontology-structure.md"
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

                # Read all rows for validation
                rows = list(reader)
                row_count = len(rows)
                
                if row_count == 0:
                    self.result.add_warning(
                        f"CSV has no data rows",
                        path=str(csv_path.relative_to(self.demo_path)),
                    )
                    return
                
                # Find potential key columns (ending with Id or ID)
                key_columns = [i for i, h in enumerate(headers) if h.lower().endswith('id')]
                
                # Determine the likely PRIMARY key column
                # For Dim/Edge tables: first ID column or column matching table name
                # For Fact tables: usually don't have a unique primary key (or use composite)
                file_name = csv_path.stem.lower()
                is_fact_or_edge = file_name.startswith('fact') or file_name.startswith('edge')
                is_dim = file_name.startswith('dim')
                is_timeseries = 'telemetry' in file_name or 'eventhouse' in str(csv_path).lower()
                
                # For fact/edge/timeseries tables, we don't enforce unique IDs
                # (they contain foreign keys that can repeat)
                if not is_fact_or_edge and not is_timeseries:
                    # For dimension tables, check the FIRST ID column for uniqueness
                    # This is typically the primary key
                    primary_key_idx = key_columns[0] if key_columns else None
                    
                    if primary_key_idx is not None:
                        col_name = headers[primary_key_idx]
                        values = [row[primary_key_idx] for row in rows if primary_key_idx < len(row)]
                        
                        # Check for NULL values
                        null_rows = [i + 2 for i, v in enumerate(values) 
                                    if not v.strip() or v.strip().lower() in ('null', 'none', '')]
                        if null_rows:
                            self.result.add_error(
                                f"Primary key column '{col_name}' has NULL/empty values in rows: {null_rows[:5]}{'...' if len(null_rows) > 5 else ''}",
                                path=str(csv_path.relative_to(self.demo_path)),
                                suggestion="Primary key columns must not contain NULL values",
                            )
                        
                        # Check for duplicates
                        if len(values) != len(set(values)):
                            duplicates = [v for v in set(values) if values.count(v) > 1]
                            self.result.add_error(
                                f"Primary key column '{col_name}' has duplicate values: {duplicates[:3]}{'...' if len(duplicates) > 3 else ''}",
                                path=str(csv_path.relative_to(self.demo_path)),
                                suggestion="Primary key values must be unique within dimension tables",
                            )
                
                # Check timestamp format for eventhouse files
                if "eventhouse" in str(csv_path).lower():
                    # Only check columns explicitly named Timestamp (not "time" which could be CycleTime, etc.)
                    timestamp_cols = [i for i, h in enumerate(headers) if h.lower() == 'timestamp']
                    for col_idx in timestamp_cols:
                        col_name = headers[col_idx]
                        # Check first few rows for ISO 8601 format
                        for row_idx, row in enumerate(rows[:5]):
                            if col_idx < len(row):
                                value = row[col_idx]
                                if value and not re.match(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', value):
                                    self.result.add_warning(
                                        f"Timestamp column '{col_name}' may not be in ISO 8601 format",
                                        path=str(csv_path.relative_to(self.demo_path)),
                                        suggestion="Use format: YYYY-MM-DDTHH:MM:SSZ",
                                    )
                                    break

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
            
            # Track static bindings across all sources
            all_static_bindings: Dict[str, List[str]] = {}
            
            # Validate lakehouse bindings
            lakehouse = bindings_data.get("lakehouse", {})
            if lakehouse:
                self._validate_yaml_source_bindings(
                    lakehouse, "lakehouse", csv_headers.get("lakehouse", {})
                )
                # Collect static bindings
                self._collect_static_bindings(lakehouse, "lakehouse", all_static_bindings)
            
            # Validate eventhouse bindings
            eventhouse = bindings_data.get("eventhouse", {})
            if eventhouse:
                self._validate_yaml_source_bindings(
                    eventhouse, "eventhouse", csv_headers.get("eventhouse", {})
                )
                # Collect static bindings
                self._collect_static_bindings(eventhouse, "eventhouse", all_static_bindings)
            
            # Check cross-source binding constraint: 1 static binding per entity across ALL sources
            for entity_name, sources in all_static_bindings.items():
                if len(sources) > 1:
                    self.result.add_error(
                        f"Entity '{entity_name}' has static bindings in multiple sources: "
                        f"{', '.join(sources)} - Fabric allows only 1 static binding per entity total",
                        suggestion="An entity can have 1 static binding (lakehouse OR eventhouse) + multiple timeseries bindings",
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

    def _collect_static_bindings(
        self,
        source_data: dict,
        source_type: str,
        all_static_bindings: Dict[str, List[str]],
    ) -> None:
        """Collect static bindings for cross-source validation."""
        entities = source_data.get("entities", [])
        for entity in entities:
            entity_name = entity.get("entity", "")
            # Detect TimeSeries binding: if timestampColumn is present, it's timeseries
            # Otherwise, check bindingType field (default to NonTimeSeries/static)
            has_timestamp = entity.get("timestampColumn") is not None
            binding_type = entity.get("bindingType", "NonTimeSeries")
            
            # Only count as static if no timestamp column AND bindingType isn't TimeSeries
            is_static = not has_timestamp and binding_type == "NonTimeSeries"
            
            if is_static:
                if entity_name not in all_static_bindings:
                    all_static_bindings[entity_name] = []
                all_static_bindings[entity_name].append(source_type)

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
        
        # Track static bindings per entity to enforce Fabric limit of 1 static binding per entity
        entity_static_bindings: Dict[str, List[str]] = {}
        
        for entity in entities:
            entity_name = entity.get("entity", "")
            # Detect TimeSeries binding: if timestampColumn is present, it's timeseries
            has_timestamp = entity.get("timestampColumn") is not None
            binding_type = entity.get("bindingType", "NonTimeSeries")
            
            # Only count as static if no timestamp column AND bindingType isn't TimeSeries
            is_static = not has_timestamp and binding_type == "NonTimeSeries"
            
            if is_static:
                if entity_name not in entity_static_bindings:
                    entity_static_bindings[entity_name] = []
                entity_static_bindings[entity_name].append(
                    f"{source_type}/{entity.get('sourceTable', 'unknown')}"
                )
            
            self._validate_yaml_entity(entity, source_type, csv_headers)
        
        # Check for multiple static bindings per entity
        for entity_name, binding_sources in entity_static_bindings.items():
            if len(binding_sources) > 1:
                self.result.add_error(
                    f"Entity '{entity_name}' has {len(binding_sources)} static bindings: "
                    f"{', '.join(binding_sources)} - Fabric allows only 1 static binding per entity",
                    suggestion="Remove duplicate static bindings or change to TimeSeries type",
                )
        
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
        
        # Validate entity name constraints
        self._validate_name_constraints(entity_name, "Entity name", f"bindings.yaml ({source_type})")
        
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
        if key_column:
            if key_column not in available_columns:
                self.result.add_error(
                    f"Entity '{entity_name}' key column '{key_column}' "
                    f"not found in {table_name}.csv",
                    suggestion=f"Available columns: {', '.join(sorted(available_columns)[:10])}",
                )
            # Track entity key for relationship validation
            self._entity_keys[entity_name] = key_column
        
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
            prop_type = prop.get("type", "")
            
            # Validate property name
            if target_prop:
                self._validate_name_constraints(target_prop, "Property name", f"bindings.yaml ({entity_name})")
                
                # Check property uniqueness across all entities
                if target_prop in self._all_property_names:
                    self.result.add_error(
                        f"Property '{target_prop}' is duplicated - property names must be unique across ALL entities",
                        path=f"bindings.yaml ({entity_name})",
                        suggestion="Rename property with entity prefix, e.g., '{entity_name}_{target_prop}'",
                    )
                self._all_property_names.add(target_prop)
            
            # Validate property type
            if prop_type:
                is_key = prop.get("is_key", False) or (source_col == key_column)
                self._validate_data_type(prop_type, f"bindings.yaml ({entity_name}.{target_prop})", is_key=is_key)
            
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
        source_entity = relationship.get("sourceEntity", "")
        target_entity = relationship.get("targetEntity", "")
        
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
        
        # CRITICAL: Check sourceKeyColumn matches source entity's key name
        if source_entity and source_key and self._entity_keys.get(source_entity):
            expected_source_key = self._entity_keys[source_entity]
            if source_key != expected_source_key:
                self.result.add_error(
                    f"Relationship '{rel_name}': sourceKeyColumn '{source_key}' "
                    f"does NOT match source entity '{source_entity}' key '{expected_source_key}'",
                    path=f"bindings.yaml (relationships)",
                    suggestion=f"Rename column to '{expected_source_key}' or create an edge table with the correct column name",
                )
        
        # Check target key column
        target_key = relationship.get("targetKeyColumn")
        if target_key and target_key not in available_columns:
            self.result.add_error(
                f"Relationship '{rel_name}' target key column "
                f"'{target_key}' not found in {table_name}.csv",
            )
        
        # CRITICAL: Check targetKeyColumn matches target entity's key name
        if target_entity and target_key and self._entity_keys.get(target_entity):
            expected_key = self._entity_keys[target_entity]
            if target_key != expected_key:
                self.result.add_error(
                    f"Relationship '{rel_name}': targetKeyColumn '{target_key}' "
                    f"does NOT match target entity '{target_entity}' key '{expected_key}'",
                    path=f"bindings.yaml (relationships)",
                    suggestion=f"Rename column to '{expected_key}' or create an edge table with the correct column name",
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
        # .demo-metadata.yaml is the primary metadata format (v3.1+)
        # demo.yaml is legacy/optional - only used for workspace config overrides
        metadata_yaml = self.demo_path / ".demo-metadata.yaml"
        if metadata_yaml.exists():
            self.result.add_info("Found .demo-metadata.yaml (v3.1+ format)")
            self._validate_metadata_yaml(metadata_yaml)

    def _validate_metadata_yaml(self, metadata_path: Path) -> None:
        """Validate .demo-metadata.yaml content."""
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = yaml.safe_load(f)
            
            if not metadata:
                return
            
            # Check entity key types
            ontology = metadata.get("ontology", {})
            entities = ontology.get("entities", [])
            for entity in entities:
                key_type = entity.get("keyType", "").lower()
                if key_type and key_type not in VALID_KEY_TYPES:
                    self.result.add_error(
                        f"Entity '{entity.get('name')}' has invalid keyType '{key_type}'",
                        path=".demo-metadata.yaml",
                        suggestion="Key types must be 'string' or 'int' only",
                    )
        except Exception as e:
            logger.warning(f"Failed to validate metadata: {e}")

    def _check_property_uniqueness(self) -> None:
        """Check that property names are unique across all entities."""
        # This is populated during binding validation
        # Report as info since validation happens during binding check
        if self._all_property_names:
            self.result.add_info(
                f"Tracked {len(self._all_property_names)} unique property names across entities"
            )

    def _check_ttl_constraints(self) -> None:
        """Validate TTL ontology file constraints."""
        ontology_dir = None
        for variant in ["ontology", "Ontology"]:
            candidate = self.demo_path / variant
            if candidate.is_dir():
                ontology_dir = candidate
                break
        
        if not ontology_dir:
            return
        
        ttl_files = list(ontology_dir.glob("*.ttl"))
        if not ttl_files:
            return
        
        ttl_path = ttl_files[0]
        try:
            with open(ttl_path, "r", encoding="utf-8") as f:
                ttl_content = f.read()
            
            # Check for xsd:decimal (not supported)
            if "xsd:decimal" in ttl_content.lower():
                self.result.add_error(
                    "TTL contains xsd:decimal which is NOT supported by Fabric Graph",
                    path=str(ttl_path.relative_to(self.demo_path)),
                    suggestion="Replace xsd:decimal with xsd:double",
                )
            
            # Check for Key: comments in entity classes
            class_pattern = re.compile(r':(\w+)\s+a\s+owl:Class\s*;[^.]*rdfs:comment\s+"([^"]*)"', re.MULTILINE | re.DOTALL)
            key_pattern = re.compile(r'Key:\s*(\w+)')
            
            for match in class_pattern.finditer(ttl_content):
                entity_name = match.group(1)
                comment = match.group(2)
                key_match = key_pattern.search(comment)
                if not key_match:
                    self.result.add_warning(
                        f"Entity '{entity_name}' missing 'Key: PropertyName' in rdfs:comment",
                        path=str(ttl_path.relative_to(self.demo_path)),
                        suggestion='Add rdfs:comment "Key: EntityId (type)" to entity class',
                    )
                else:
                    key_name = key_match.group(1)
                    # Verify the key property exists as a DatatypeProperty
                    if f":{key_name} a owl:DatatypeProperty" not in ttl_content:
                        self.result.add_warning(
                            f"Entity '{entity_name}' references key '{key_name}' but no matching DatatypeProperty found",
                            path=str(ttl_path.relative_to(self.demo_path)),
                        )
            
            # Check for timeseries annotation on eventhouse properties
            # Properties bound to Eventhouse should have "(timeseries)" in rdfs:comment
            self._check_timeseries_annotations(ttl_content, ttl_path)
                    
        except Exception as e:
            logger.warning(f"Failed to validate TTL: {e}")

    def _check_timeseries_annotations(self, ttl_content: str, ttl_path: Path) -> None:
        """
        Check that timeseries properties have the (timeseries) annotation in rdfs:comment.
        
        Per .agentic/agent-instructions.md Phase 3:
        Properties bound to Eventhouse must have "(timeseries)" in rdfs:comment to be
        correctly classified. Without this, eventhouse properties may be incorrectly
        bound as static properties.
        """
        # Check if there's eventhouse data to warrant timeseries properties
        eventhouse_dir = None
        for variant in ["eventhouse", "Eventhouse"]:
            candidate = self.demo_path / "data" / variant
            if not candidate.is_dir():
                candidate = self.demo_path / "Data" / variant
            if candidate.is_dir():
                eventhouse_dir = candidate
                break
        
        if not eventhouse_dir:
            return  # No eventhouse data, no timeseries validation needed
        
        # Find properties with (timeseries) annotation
        timeseries_pattern = re.compile(
            r':(\w+)\s+a\s+owl:DatatypeProperty\s*;[^.]*rdfs:comment\s+"([^"]*\(timeseries\)[^"]*)"',
            re.MULTILINE | re.DOTALL | re.IGNORECASE
        )
        timeseries_props = set()
        for match in timeseries_pattern.finditer(ttl_content):
            timeseries_props.add(match.group(1))
        
        if timeseries_props:
            self.result.add_info(
                f"Found {len(timeseries_props)} timeseries-annotated properties in TTL",
                path=str(ttl_path.relative_to(self.demo_path)),
            )
        else:
            # Check if there are properties that look like timeseries but lack annotation
            # Common patterns: Temperature, Level, Pressure, FlowRate, Telemetry, OEE, etc.
            telemetry_keywords = [
                'temperature', 'temp', 'level', 'pressure', 'flowrate', 'flow',
                'oee', 'velocity', 'consumption', 'power', 'cycle', 'speed',
                'telemetry', 'reading', 'sensor', 'metric'
            ]
            
            # Find all DatatypeProperties
            prop_pattern = re.compile(r':(\w+)\s+a\s+owl:DatatypeProperty', re.MULTILINE)
            potential_timeseries = []
            for match in prop_pattern.finditer(ttl_content):
                prop_name = match.group(1).lower()
                for keyword in telemetry_keywords:
                    if keyword in prop_name:
                        potential_timeseries.append(match.group(1))
                        break
            
            if potential_timeseries and len(list(eventhouse_dir.glob("*.csv"))) > 0:
                self.result.add_warning(
                    f"Eventhouse data exists but no timeseries annotations found in TTL. "
                    f"Properties like {potential_timeseries[:3]} may need '(timeseries)' in rdfs:comment",
                    path=str(ttl_path.relative_to(self.demo_path)),
                    suggestion="Add (timeseries) to rdfs:comment for Eventhouse-bound properties",
                )

    def _validate_name_constraints(self, name: str, name_type: str, context: str) -> None:
        """
        Validate name against Fabric Ontology constraints using SDK validation.
        
        Phase 4: Now uses SDK's validate_name() function for authoritative validation,
        with additional demo-specific length checks (26 chars recommended for demos).
        """
        if not name:
            return
        
        # Demo-specific: Check length (1-26 characters for optimal Graph queries)
        # SDK allows 128 chars, but demos should use shorter names
        if len(name) > RECOMMENDED_NAME_LENGTH:
            self.result.add_warning(
                f"{name_type} '{name}' exceeds recommended {RECOMMENDED_NAME_LENGTH} character limit ({len(name)} chars)",
                path=context,
                suggestion=f"Consider shortening to {RECOMMENDED_NAME_LENGTH} characters or less for optimal Graph query compatibility",
            )
        
        # Use SDK validation for name pattern and reserved words
        try:
            # Capture warnings from SDK validation
            warnings_collected = []
            def collect_warning(msg: str) -> None:
                warnings_collected.append(msg)
            
            sdk_validate_name(
                name=name, 
                field_name=name_type, 
                allow_reserved=False,
                warn_callback=collect_warning,
            )
            
            # Add any SDK warnings to our result
            for warning in warnings_collected:
                self.result.add_warning(warning, path=context)
                
        except SDKValidationError as e:
            # SDK validation failed - add as error
            self.result.add_error(
                f"{name_type} '{name}' validation failed: {e.message}",
                path=context,
                suggestion=e.details.get("suggestion") if e.details else None,
            )
        
        # Fallback: Check pattern (for demo-specific shorter pattern)
        # SDK pattern allows 128 chars, demo pattern is stricter (26 chars)
        if len(name) > 1 and not NAME_PATTERN.match(name) and len(name) <= 26:
            self.result.add_info(
                f"{name_type} '{name}' doesn't match demo naming pattern (may still be valid for API)",
                path=context,
                suggestion="Use alphanumeric characters, hyphens, underscores; start/end with alphanumeric",
            )

    def _validate_data_type(self, data_type: str, context: str, is_key: bool = False) -> None:
        """
        Validate data type against Fabric Graph constraints using SDK validation.
        
        Phase 4: Uses SDK's validate_data_type() function for authoritative validation.
        """
        if not data_type:
            return
        
        type_lower = data_type.lower()
        
        # Map common aliases to SDK types for validation
        type_mapping = {
            "string": "String", "str": "String",
            "int": "BigInt", "integer": "BigInt", "long": "BigInt", "int64": "BigInt", "bigint": "BigInt",
            "double": "Double", "float": "Float",
            "boolean": "Boolean", "bool": "Boolean",
            "datetime": "DateTime", "datetimeoffset": "DateTime",
            "decimal": "Decimal",  # Will fail SDK validation
        }
        
        sdk_type = type_mapping.get(type_lower, data_type)
        
        # Use SDK validation for data type
        try:
            sdk_validate_data_type(sdk_type)
        except SDKValidationError as e:
            self.result.add_error(
                f"Data type '{data_type}' validation failed: {e.message}",
                path=context,
                suggestion=e.details.get("suggestion") if e.details else "Use a valid type: String, BigInt, Double, Boolean, DateTime, Float",
            )
            return
        
        # Check for invalid types that SDK explicitly rejects
        if type_lower in INVALID_TYPES:
            self.result.add_error(
                f"Data type '{data_type}' is NOT supported by Fabric Graph (returns NULL)",
                path=context,
                suggestion="Use 'double' instead of 'decimal' for precision values",
            )
        
        # Check key types
        if is_key and type_lower not in VALID_KEY_TYPES:
            self.result.add_error(
                f"Key type '{data_type}' is invalid - keys must be string or int only",
                path=context,
                suggestion="Change key type to 'string' or 'int'",
            )


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
