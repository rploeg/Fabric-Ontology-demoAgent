"""Fabric Ontology Demo Automation Tool.

Automates the setup of Fabric Ontology demos:
- Create Lakehouse → Upload CSVs → Load tables
- Create Eventhouse → KQL Database → Ingest telemetry
- Create Ontology → Bind data sources → Refresh graph
"""

__version__ = "1.0.0"

from fabric_demo.client import FabricClient, FabricAPIError
from fabric_demo.loader import DemoLoader, DemoPackage, BindingParser
from fabric_demo.state import StateManager
from fabric_demo.runner import SetupRunner

__all__ = [
    "FabricClient",
    "FabricAPIError",
    "DemoLoader",
    "DemoPackage",
    "BindingParser",
    "StateManager",
    "SetupRunner",
]
