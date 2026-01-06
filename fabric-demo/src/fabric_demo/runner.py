"""Orchestrates demo setup with resume capability."""

from pathlib import Path
from typing import Callable, Optional

from fabric_demo.client import FabricClient
from fabric_demo.errors import SetupError
from fabric_demo.loader import DemoLoader, DemoPackage
from fabric_demo.state import StateManager


class SetupRunner:
    """Orchestrates demo setup with resume capability.

    This class coordinates the setup of a Fabric Ontology demo:
    1. Creates Lakehouse and loads CSV data as Delta tables
    2. Creates Eventhouse and KQL database for timeseries data
    3. Creates Ontology, binds data sources, and refreshes graph

    Setup is resumable - if it fails, re-running will skip completed steps.
    """

    def __init__(self, demo_path: Path | str, workspace_id: str):
        """Initialize setup runner.

        Args:
            demo_path: Path to the demo package folder
            workspace_id: Target Fabric workspace ID
        """
        self.demo_path = Path(demo_path)
        self.workspace_id = workspace_id
        self.state = StateManager(demo_path)
        self.client = FabricClient(workspace_id)
        self.demo: Optional[DemoPackage] = None

    def setup(self, force: bool = False) -> bool:
        """Run setup, returns True on success.

        Args:
            force: If True, restart from beginning ignoring previous state

        Returns:
            True if setup completed successfully
        """
        # Handle force restart
        if force:
            self.state.delete()
            self.state = StateManager(self.demo_path)

        # Check if already complete
        if self.state.status == "completed":
            print("✅ Setup already completed. Use --force to redo.")
            return True

        # Load and validate demo package
        print(f"\n📦 Setting up: {self.demo_path.name}")
        print("━" * 50)

        loader = DemoLoader(self.demo_path)

        # Validate first
        validation_errors = loader.validate()
        if validation_errors:
            print("\n❌ Validation errors:")
            for error in validation_errors:
                print(f"   • {error}")
            return False

        self.demo = loader.load()
        self.state.set_workspace(self.workspace_id)

        try:
            self._run_steps()
            self.state.mark_completed()
            self._print_summary()
            return True
        except Exception as e:
            self.state.set_error(str(e))
            print(f"\n❌ Setup failed: {e}")
            print("   Run again to resume from last successful step.")
            return False

    def _run_steps(self) -> None:
        """Execute all setup steps."""
        assert self.demo is not None

        # 1. Lakehouse setup
        if self.demo.lakehouse_csvs:
            self._step("create_lakehouse", self._create_lakehouse)

            # Upload CSVs
            for csv in self.demo.lakehouse_csvs:
                step_name = f"upload_{csv.stem}"
                self._step(step_name, lambda c=csv: self._upload_csv(c))

            # Load tables (convert CSV to Delta)
            for csv in self.demo.lakehouse_csvs:
                step_name = f"load_{csv.stem}"
                self._step(step_name, lambda c=csv: self._load_table(c))

        # 2. Eventhouse setup (if has timeseries data)
        if self.demo.eventhouse_csvs:
            self._step("create_eventhouse", self._create_eventhouse)
            self._step("create_kql_database", self._create_kql_database)

            # Note: KQL ingestion is simplified - full implementation would use Kusto SDK
            for csv in self.demo.eventhouse_csvs:
                step_name = f"ingest_{csv.stem}"
                self._step(step_name, lambda c=csv: self._ingest_kql(c))

        # 3. Ontology setup
        self._step("create_ontology", self._create_ontology)
        self._step("bind_ontology", self._bind_ontology)
        self._step("refresh_graph", self._refresh_graph)

    def _step(self, name: str, func: Callable) -> None:
        """Execute step with skip-if-done logic.

        Args:
            name: Step name for tracking
            func: Function to execute
        """
        if self.state.is_done(name):
            print(f"  ⏭️  {name} - skipped (done)")
            return

        print(f"  ⏳ {name}...", end=" ", flush=True)
        try:
            result = func()
            self.state.mark_done(name, result)
            print("✅")
        except Exception as e:
            print("❌")
            raise SetupError(f"Step '{name}' failed: {e}") from e

    # --- Step Implementations ---

    def _create_lakehouse(self) -> str:
        """Create lakehouse for demo."""
        assert self.demo is not None
        name = f"{self.demo.name}-Lakehouse"
        return self.client.create_lakehouse(name)

    def _upload_csv(self, csv: Path) -> None:
        """Upload a CSV file to OneLake."""
        lh_id = self.state.resources.get("lakehouse_id")
        if not lh_id:
            raise SetupError("Lakehouse ID not found in state")

        content = csv.read_bytes()
        self.client.upload_file(lh_id, f"Files/{csv.name}", content)

    def _load_table(self, csv: Path) -> None:
        """Load CSV into Delta table."""
        lh_id = self.state.resources.get("lakehouse_id")
        if not lh_id:
            raise SetupError("Lakehouse ID not found in state")

        self.client.load_table(lh_id, csv.stem, f"Files/{csv.name}")

    def _create_eventhouse(self) -> str:
        """Create eventhouse for timeseries data."""
        assert self.demo is not None
        name = f"{self.demo.name}-Eventhouse"
        return self.client.create_eventhouse(name)

    def _create_kql_database(self) -> str:
        """Create KQL database under eventhouse."""
        assert self.demo is not None
        eh_id = self.state.resources.get("eventhouse_id")
        if not eh_id:
            raise SetupError("Eventhouse ID not found in state")

        name = f"{self.demo.name}-KQL"
        return self.client.create_kql_database(name, eh_id)

    def _ingest_kql(self, csv: Path) -> None:
        """Ingest CSV data into KQL table.

        Note: This is a simplified placeholder. Full implementation
        would use Kusto SDK for schema creation and data ingestion.
        """
        # TODO: Implement full KQL ingestion using Kusto SDK
        # For now, this is a placeholder that marks the step complete
        # Real implementation would:
        # 1. Connect to KQL database using Kusto SDK
        # 2. Create table with schema inferred from CSV
        # 3. Ingest CSV data into table
        pass

    def _create_ontology(self) -> str:
        """Create ontology from TTL file."""
        assert self.demo is not None
        name = f"{self.demo.name}-Ontology"
        ttl_content = self.demo.ttl_file.read_text(encoding="utf-8")  # type: ignore
        return self.client.create_ontology(name, ttl_content)

    def _bind_ontology(self) -> None:
        """Bind data sources to ontology."""
        assert self.demo is not None
        ont_id = self.state.resources.get("ontology_id")
        if not ont_id:
            raise SetupError("Ontology ID not found in state")

        ttl_content = self.demo.ttl_file.read_text(encoding="utf-8")  # type: ignore
        bindings = self._build_bindings()
        self.client.bind_ontology(ont_id, ttl_content, bindings)

    def _build_bindings(self) -> dict:
        """Build bindings JSON from parsed markdown."""
        assert self.demo is not None
        lh_id = self.state.resources.get("lakehouse_id")
        kql_id = self.state.resources.get("kql_database_id")

        bindings = []

        # Lakehouse bindings
        for b in self.demo.lakehouse_bindings:
            bindings.append(
                {
                    "entityId": b["entityId"],
                    "entityName": b["entityName"],
                    "source": {
                        "type": "lakehouse",
                        "connectionId": lh_id,
                        "table": b["table"],
                    },
                    "propertyMappings": b["propertyMappings"],
                }
            )

        # Eventhouse bindings
        for b in self.demo.eventhouse_bindings:
            bindings.append(
                {
                    "entityId": b["entityId"],
                    "entityName": b["entityName"],
                    "source": {
                        "type": "kql",
                        "connectionId": kql_id,
                        "table": b["table"],
                    },
                    "propertyMappings": b["propertyMappings"],
                }
            )

        return {"bindings": bindings}

    def _refresh_graph(self) -> None:
        """Trigger graph refresh for ontology."""
        ont_id = self.state.resources.get("ontology_id")
        if not ont_id:
            raise SetupError("Ontology ID not found in state")

        self.client.refresh_ontology_graph(ont_id)

    def _print_summary(self) -> None:
        """Print completion summary."""
        print("\n" + "═" * 50)
        print("✅ Setup complete!")
        print("═" * 50)
        print(f"\nResources created:")
        for key, value in self.state.resources.items():
            if value:
                print(f"  {key}: {value}")


class CleanupRunner:
    """Removes resources created by setup."""

    def __init__(self, demo_path: Path | str, workspace_id: str):
        """Initialize cleanup runner.

        Args:
            demo_path: Path to the demo package folder
            workspace_id: Target Fabric workspace ID
        """
        self.demo_path = Path(demo_path)
        self.workspace_id = workspace_id
        self.state = StateManager(demo_path)
        self.client = FabricClient(workspace_id)

    def cleanup(self, confirm: bool = True) -> bool:
        """Remove all resources created by setup.

        Args:
            confirm: If True, prompt for confirmation

        Returns:
            True if cleanup completed successfully
        """
        resources = self.state.resources

        # Check if there's anything to clean up
        has_resources = any(v for v in resources.values() if v)
        if not has_resources:
            print("No resources found to clean up.")
            return True

        # Show what will be deleted
        print("\n🗑️  Resources to delete:")
        for key, value in resources.items():
            if value:
                print(f"  • {key}: {value}")

        if confirm:
            response = input("\nProceed with cleanup? [y/N]: ")
            if response.lower() != "y":
                print("Cleanup cancelled.")
                return False

        print("\n🧹 Cleaning up...")

        # Delete in reverse order of creation
        try:
            if resources.get("ontology_id"):
                print("  ⏳ Deleting ontology...", end=" ", flush=True)
                self.client.delete_ontology(resources["ontology_id"])
                print("✅")

            if resources.get("kql_database_id"):
                print("  ⏳ Deleting KQL database...", end=" ", flush=True)
                self.client.delete_kql_database(resources["kql_database_id"])
                print("✅")

            if resources.get("eventhouse_id"):
                print("  ⏳ Deleting eventhouse...", end=" ", flush=True)
                self.client.delete_eventhouse(resources["eventhouse_id"])
                print("✅")

            if resources.get("lakehouse_id"):
                print("  ⏳ Deleting lakehouse...", end=" ", flush=True)
                self.client.delete_lakehouse(resources["lakehouse_id"])
                print("✅")

            # Delete state file
            self.state.delete()
            print("\n✅ Cleanup complete!")
            return True

        except Exception as e:
            print(f"\n❌ Cleanup failed: {e}")
            return False
