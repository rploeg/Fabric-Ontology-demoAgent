"""
Pytest configuration and fixtures.
"""

import pytest
from pathlib import Path


@pytest.fixture
def sample_demo_path(tmp_path) -> Path:
    """Create a sample demo package structure for testing."""
    demo_path = tmp_path / "SampleDemo"
    demo_path.mkdir()

    # Create directories
    (demo_path / "ontology").mkdir()
    (demo_path / "data").mkdir()
    (demo_path / "data" / "lakehouse").mkdir()
    (demo_path / "data" / "eventhouse").mkdir()
    (demo_path / "bindings").mkdir()
    (demo_path / "queries").mkdir()

    # Create TTL file
    ttl_content = """
@prefix bd: <http://example.org/bd-medical/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

bd:Product a owl:Class ;
    rdfs:label "Product" .

bd:Facility a owl:Class ;
    rdfs:label "Facility" .
"""
    (demo_path / "ontology" / "bd-medical.ttl").write_text(ttl_content)

    # Create lakehouse CSV files
    (demo_path / "data" / "lakehouse" / "DimProduct.csv").write_text(
        "ProductID,Name,Category\n1,Widget,Electronics\n2,Gadget,Electronics\n"
    )
    (demo_path / "data" / "lakehouse" / "DimFacility.csv").write_text(
        "FacilityID,Name,Location\n1,Plant A,New York\n2,Plant B,Chicago\n"
    )

    # Create eventhouse CSV files
    (demo_path / "data" / "eventhouse" / "BatchTelemetry.csv").write_text(
        "BatchID,PreciseTimestamp,Temperature,Pressure\n"
        "B001,2024-01-01T10:00:00Z,72.5,14.7\n"
        "B001,2024-01-01T10:01:00Z,73.0,14.8\n"
    )

    # Create binding files
    (demo_path / "bindings" / "lakehouse-binding.md").write_text("""
# Lakehouse Bindings

## Entity: Product
Table: DimProduct
Key: ProductID

| Column | Property |
|--------|----------|
| ProductID | id |
| Name | name |
| Category | category |

## Entity: Facility
Table: DimFacility
Key: FacilityID

| Column | Property |
|--------|----------|
| FacilityID | id |
| Name | name |
| Location | location |
""")

    (demo_path / "bindings" / "eventhouse-binding.md").write_text("""
# Eventhouse Bindings

## Entity: BatchTelemetry
Table: BatchTelemetry
Key: BatchID
Timestamp: PreciseTimestamp

| Column | Property |
|--------|----------|
| BatchID | batchId |
| Temperature | temperature |
| Pressure | pressure |
""")

    # Create README
    (demo_path / "README.md").write_text(f"# {demo_path.name}\n\nSample demo for testing.")

    # Create demo.yaml
    demo_yaml = """
demo:
  name: SampleDemo
  description: Sample demo for testing

fabric:
  workspace_id: ${FABRIC_WORKSPACE_ID}

options:
  skip_existing: true
  dry_run: false
"""
    (demo_path / "demo.yaml").write_text(demo_yaml)

    return demo_path


@pytest.fixture
def minimal_demo_path(tmp_path) -> Path:
    """Create a minimal demo package structure."""
    demo_path = tmp_path / "MinimalDemo"
    demo_path.mkdir()

    (demo_path / "ontology").mkdir()
    (demo_path / "data").mkdir()
    (demo_path / "data" / "lakehouse").mkdir()

    (demo_path / "ontology" / "test.ttl").write_text("# Minimal ontology")
    (demo_path / "data" / "lakehouse" / "test.csv").write_text("ID,Name\n1,Test\n")

    return demo_path
