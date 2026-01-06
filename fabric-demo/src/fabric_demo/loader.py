"""Auto-discover demo contents and parse bindings from markdown."""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from fabric_demo.errors import DemoValidationError


@dataclass
class DemoPackage:
    """Discovered demo package contents."""

    name: str
    path: Path

    # Files
    lakehouse_csvs: List[Path] = field(default_factory=list)
    eventhouse_csvs: List[Path] = field(default_factory=list)
    ttl_file: Optional[Path] = None

    # Parsed bindings
    lakehouse_bindings: List[dict] = field(default_factory=list)
    eventhouse_bindings: List[dict] = field(default_factory=list)

    def __str__(self) -> str:
        return (
            f"DemoPackage({self.name})\n"
            f"  Lakehouse CSVs: {len(self.lakehouse_csvs)}\n"
            f"  Eventhouse CSVs: {len(self.eventhouse_csvs)}\n"
            f"  TTL file: {self.ttl_file.name if self.ttl_file else 'None'}\n"
            f"  Lakehouse bindings: {len(self.lakehouse_bindings)}\n"
            f"  Eventhouse bindings: {len(self.eventhouse_bindings)}"
        )


class BindingParser:
    """Parse entity bindings from markdown tables.

    Expected markdown format:

    ## Entity: Product (ID: 1000000000001)
    **Table:** DimProduct

    | Property | Column | Key |
    |----------|--------|-----|
    | productId | ProductId | Yes |
    | name | ProductName | No |
    """

    # Pattern for entity headers: ## Entity: Product (ID: 1000000000001)
    ENTITY_HEADER = re.compile(r"##\s*Entity:\s*(\w+)\s*\(ID:\s*(\d+)\)", re.IGNORECASE)

    # Pattern for table source: **Table:** DimProduct
    TABLE_SOURCE = re.compile(r"\*\*Table:\*\*\s*(\w+)", re.IGNORECASE)

    # Pattern for markdown table rows: | prop | col | key |
    TABLE_ROW = re.compile(r"\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|")

    @classmethod
    def parse(cls, content: str) -> List[dict]:
        """Parse binding markdown into structured format.

        Args:
            content: The markdown content to parse

        Returns:
            List of binding dictionaries with entityName, entityId, table, propertyMappings
        """
        bindings: List[dict] = []
        current_entity: Optional[dict] = None

        for line in content.split("\n"):
            # Check for entity header
            entity_match = cls.ENTITY_HEADER.search(line)
            if entity_match:
                # Save previous entity if exists
                if current_entity:
                    bindings.append(current_entity)
                current_entity = {
                    "entityName": entity_match.group(1),
                    "entityId": entity_match.group(2),
                    "table": None,
                    "propertyMappings": [],
                }
                continue

            # Check for table source
            table_match = cls.TABLE_SOURCE.search(line)
            if table_match and current_entity:
                current_entity["table"] = table_match.group(1)
                continue

            # Check for property mapping row
            if current_entity:
                row_match = cls.TABLE_ROW.search(line)
                if row_match:
                    prop, col, key_str = row_match.groups()
                    prop, col = prop.strip(), col.strip()

                    # Skip header row and separator
                    if prop.lower() in ("property", "ontology property", "---", "-"):
                        continue
                    if "-" * 3 in prop:  # Skip markdown separator
                        continue

                    is_key = key_str.strip().lower() in ("yes", "true", "✓", "key", "x")
                    current_entity["propertyMappings"].append(
                        {"property": prop, "column": col, "isKey": is_key}
                    )

        # Don't forget the last entity
        if current_entity:
            bindings.append(current_entity)

        return bindings


class DemoLoader:
    """Auto-discover demo contents and parse bindings."""

    def __init__(self, demo_path: Path | str):
        """Initialize loader with path to demo folder.

        Args:
            demo_path: Path to the demo package folder
        """
        self.demo_path = Path(demo_path).resolve()
        self.name = self.demo_path.name

    def load(self) -> DemoPackage:
        """Load and validate demo package.

        Returns:
            DemoPackage with discovered files and parsed bindings

        Raises:
            DemoValidationError: If required files are missing
        """
        # Validate demo path exists
        if not self.demo_path.exists():
            raise DemoValidationError(f"Demo path does not exist: {self.demo_path}")

        if not self.demo_path.is_dir():
            raise DemoValidationError(f"Demo path is not a directory: {self.demo_path}")

        # Find TTL file (required)
        ttl_file = self._find_ttl_file()

        return DemoPackage(
            name=self.name,
            path=self.demo_path,
            lakehouse_csvs=self._find_lakehouse_csvs(),
            eventhouse_csvs=self._find_eventhouse_csvs(),
            ttl_file=ttl_file,
            lakehouse_bindings=self._parse_binding("lakehouse-binding.md"),
            eventhouse_bindings=self._parse_binding("eventhouse-binding.md"),
        )

    def _find_lakehouse_csvs(self) -> List[Path]:
        """Find all CSV files in data/lakehouse/."""
        lakehouse_dir = self.demo_path / "data" / "lakehouse"
        if not lakehouse_dir.exists():
            return []
        return sorted(lakehouse_dir.glob("*.csv"))

    def _find_eventhouse_csvs(self) -> List[Path]:
        """Find all CSV files in data/eventhouse/."""
        eventhouse_dir = self.demo_path / "data" / "eventhouse"
        if not eventhouse_dir.exists():
            return []
        return sorted(eventhouse_dir.glob("*.csv"))

    def _find_ttl_file(self) -> Path:
        """Find the TTL ontology file.

        Returns:
            Path to the TTL file

        Raises:
            DemoValidationError: If no TTL file found
        """
        ontology_dir = self.demo_path / "ontology"
        if not ontology_dir.exists():
            raise DemoValidationError(f"Ontology directory not found: {ontology_dir}")

        ttl_files = list(ontology_dir.glob("*.ttl"))
        if not ttl_files:
            raise DemoValidationError(f"No .ttl file found in {ontology_dir}")

        if len(ttl_files) > 1:
            # Use the first one, but warn
            print(f"  ⚠️  Multiple TTL files found, using: {ttl_files[0].name}")

        return ttl_files[0]

    def _parse_binding(self, filename: str) -> List[dict]:
        """Parse binding from markdown file.

        Args:
            filename: Name of the binding file (e.g., "lakehouse-binding.md")

        Returns:
            List of parsed bindings, or empty list if file doesn't exist
        """
        binding_file = self.demo_path / "bindings" / filename
        if not binding_file.exists():
            return []

        content = binding_file.read_text(encoding="utf-8")
        return BindingParser.parse(content)

    def validate(self) -> List[str]:
        """Validate demo package structure.

        Returns:
            List of validation errors (empty if valid)
        """
        errors: List[str] = []

        # Check required directories
        if not (self.demo_path / "ontology").exists():
            errors.append("Missing 'ontology' directory")

        if not (self.demo_path / "data").exists():
            errors.append("Missing 'data' directory")

        # Check for at least one data source
        has_lakehouse = (self.demo_path / "data" / "lakehouse").exists()
        has_eventhouse = (self.demo_path / "data" / "eventhouse").exists()
        if not has_lakehouse and not has_eventhouse:
            errors.append("No data source found (need data/lakehouse or data/eventhouse)")

        # Check for TTL file
        ontology_dir = self.demo_path / "ontology"
        if ontology_dir.exists() and not list(ontology_dir.glob("*.ttl")):
            errors.append("No .ttl file found in ontology directory")

        # Check bindings match data
        if has_lakehouse:
            binding_file = self.demo_path / "bindings" / "lakehouse-binding.md"
            if not binding_file.exists():
                errors.append("Missing bindings/lakehouse-binding.md")

        if has_eventhouse:
            binding_file = self.demo_path / "bindings" / "eventhouse-binding.md"
            if not binding_file.exists():
                errors.append("Missing bindings/eventhouse-binding.md")

        return errors
