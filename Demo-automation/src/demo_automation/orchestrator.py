"""
Demo Orchestrator for coordinating the complete demo setup process.

Manages the execution of all setup steps including:
1. Lakehouse creation and data upload
2. Eventhouse creation and data ingestion
3. Ontology creation and binding configuration
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.panel import Panel

from .core.config import DemoConfiguration, ExistingResourceAction
from .core.errors import (
    DemoAutomationError,
    ResourceExistsError,
    CancellationRequestedError,
)
from .core.global_config import GlobalConfig
from .platform import FabricClient, OneLakeDataClient, LakehouseClient, EventhouseClient
from .platform.fabric_client import RateLimitConfig
from .binding import (
    OntologyBindingBuilder,  # Legacy - deprecated, kept for backwards compatibility
    BindingType,
    parse_demo_bindings,
    get_eventhouse_table_configs,
    parse_bindings_yaml,
    YamlBindingsConfig,
    # SDK Bridge (recommended)
    SDKBindingBridge,
    EntityBindingConfig,
    RelationshipContextConfig,
)
from .state_manager import SetupStateManager, SetupStatus as PersistentSetupStatus
from .ontology import parse_ttl_file
from .ontology.sdk_converter import (
    ttl_to_sdk_builder,
    ttl_entity_to_sdk_info,
    ttl_relationship_to_sdk_info,
    ttl_result_to_sdk_infos,
    create_bridge_from_ttl,
)
from .sdk_adapter import (
    create_sdk_client,
    create_ontology_builder,
    map_ttl_type_to_string,
)

# SDK validation for pre-flight checks (Phase 4)
from fabric_ontology.validation import OntologyValidator as SDKOntologyValidator
from fabric_ontology.exceptions import ValidationError as SDKValidationError


logger = logging.getLogger(__name__)
console = Console()


class StepStatus(Enum):
    """Status of an execution step."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StepResult:
    """Result of a single step execution."""
    status: StepStatus
    message: str = ""
    artifact_id: Optional[str] = None
    artifact_name: Optional[str] = None
    error: Optional[Exception] = None
    duration_seconds: float = 0
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SetupState:
    """State tracking for demo setup."""
    lakehouse_id: Optional[str] = None
    lakehouse_name: Optional[str] = None
    eventhouse_id: Optional[str] = None
    eventhouse_name: Optional[str] = None
    kql_database_id: Optional[str] = None
    kql_database_name: Optional[str] = None
    ontology_id: Optional[str] = None
    ontology_name: Optional[str] = None
    uploaded_files: List[str] = field(default_factory=list)
    loaded_tables: List[str] = field(default_factory=list)
    ingested_tables: List[str] = field(default_factory=list)
    bindings_configured: bool = False


class DemoOrchestrator:
    """
    Orchestrates the complete demo setup process.

    Execution flow:
    1. Validate configuration
    2. Create Lakehouse (if enabled)
    3. Upload CSV files to Lakehouse (skip if tables already exist)
    4. Load CSV to Delta tables (skip if tables already exist)
    5. Create Eventhouse (if enabled)
    6. Ingest data to KQL tables (skip if tables already exist)
    7. Create Ontology (if enabled)
    8. Configure data bindings
    9. Comprehensive verification
    10. Refresh graph (manual step to sync data)
    """

    def __init__(
        self,
        config: DemoConfiguration,
        progress_callback: Optional[Callable[[str, str, float], None]] = None,
        resume: bool = False,
    ):
        """
        Initialize the orchestrator.

        Args:
            config: Demo configuration
            progress_callback: Optional callback(step_name, status, percent)
            resume: If True, attempt to resume from previous state
        """
        self.config = config
        self.progress_callback = progress_callback
        self.state = SetupState()
        self._cancelled = False
        self._resume = resume

        # State manager for persistence
        self._state_manager = SetupStateManager(
            demo_path=config.demo_path,
            workspace_id=config.fabric.workspace_id,
            demo_name=config.name,
        )

        # Clients (initialized lazily)
        self._fabric_client: Optional[FabricClient] = None
        self._onelake_client: Optional[OneLakeDataClient] = None
        self._lakehouse_client: Optional[LakehouseClient] = None
        self._eventhouse_client: Optional[EventhouseClient] = None

    def cancel(self) -> None:
        """Request cancellation of the current operation."""
        self._cancelled = True
        logger.warning("Cancellation requested")

    def _check_cancellation(self) -> None:
        """Check if cancellation was requested."""
        if self._cancelled:
            raise CancellationRequestedError("Operation cancelled by user")

    def _handle_existing_resource(
        self,
        resource_type: str,
        resource_name: str,
        existing_id: str,
    ) -> tuple[bool, str]:
        """
        Handle the case when a resource already exists.

        Args:
            resource_type: Type of resource (e.g., "Lakehouse", "Ontology")
            resource_name: Name of the existing resource
            existing_id: ID of the existing resource

        Returns:
            Tuple of (should_skip, message)
            - should_skip=True means use existing resource
            - should_skip=False means raise an error

        Raises:
            ResourceExistsError: If action is FAIL
            CancellationRequestedError: If user declines in interactive mode
        """
        action = self.config.options.get_existing_action()

        if action == ExistingResourceAction.SKIP:
            return True, f"{resource_type} already exists: {resource_name}"

        elif action == ExistingResourceAction.PROMPT:
            # Interactive mode - ask user
            console.print(f"\n[yellow]⚠ {resource_type} '{resource_name}' already exists[/yellow]")
            console.print(f"  ID: {existing_id}")

            while True:
                response = console.input(
                    "\n[bold]Use existing resource? [Y/n/q]:[/bold] "
                ).strip().lower()

                if response in ("", "y", "yes"):
                    console.print(f"[green]→ Using existing {resource_type}[/green]")
                    return True, f"{resource_type} already exists (user confirmed): {resource_name}"
                elif response in ("n", "no"):
                    raise ResourceExistsError(
                        f"{resource_type} '{resource_name}' already exists (user declined)",
                        resource_type=resource_type,
                        resource_name=resource_name,
                    )
                elif response in ("q", "quit"):
                    raise CancellationRequestedError("User cancelled setup")
                else:
                    console.print("[dim]Please enter Y (yes), N (no), or Q (quit)[/dim]")

        elif action == ExistingResourceAction.FAIL:
            raise ResourceExistsError(
                f"{resource_type} '{resource_name}' already exists",
                resource_type=resource_type,
                resource_name=resource_name,
            )

        else:
            # Default to skip
            return True, f"{resource_type} already exists: {resource_name}"

    @property
    def fabric_client(self) -> FabricClient:
        """Get or create FabricClient."""
        if self._fabric_client is None:
            # Load global config for rate limiting settings
            global_config = GlobalConfig.load()
            rate_limit_config = RateLimitConfig(
                enabled=global_config.rate_limit_enabled,
                requests_per_minute=global_config.rate_limit_requests_per_minute,
                burst=global_config.rate_limit_burst,
            )
            self._fabric_client = FabricClient(
                workspace_id=self.config.fabric.workspace_id,
                tenant_id=self.config.fabric.tenant_id,
                use_interactive_auth=self.config.fabric.use_interactive_auth,
                rate_limit_config=rate_limit_config,
            )
        return self._fabric_client

    @property
    def onelake_client(self) -> OneLakeDataClient:
        """Get or create OneLakeDataClient."""
        if self._onelake_client is None:
            # OneLake client needs workspace name
            # For now, use workspace_id - would need to resolve name in production
            self._onelake_client = OneLakeDataClient(
                workspace_name=self.config.fabric.workspace_id,
                credential=self.fabric_client._credential,
            )
        return self._onelake_client

    @property
    def lakehouse_client(self) -> LakehouseClient:
        """Get or create LakehouseClient."""
        if self._lakehouse_client is None:
            self._lakehouse_client = LakehouseClient(
                fabric_client=self.fabric_client,
                workspace_id=self.config.fabric.workspace_id,
            )
        return self._lakehouse_client

    @property
    def eventhouse_client(self) -> EventhouseClient:
        """Get or create EventhouseClient."""
        if self._eventhouse_client is None:
            self._eventhouse_client = EventhouseClient(
                fabric_client=self.fabric_client,
                workspace_id=self.config.fabric.workspace_id,
            )
        return self._eventhouse_client

    def run_setup(self, dry_run: bool = False) -> Dict[str, StepResult]:
        """
        Execute the complete demo setup.

        Args:
            dry_run: If True, only validate without making changes

        Returns:
            Dict mapping step names to results
        """
        results: Dict[str, StepResult] = {}

        if dry_run:
            console.print(Panel("[yellow]DRY RUN MODE[/yellow] - No changes will be made"))

        # Check for existing state and handle resume
        if self._resume and self._state_manager.has_existing_state():
            existing_state = self._state_manager.load_state()
            if existing_state and existing_state.can_resume():
                self._handle_resume(existing_state)
                console.print(Panel(
                    f"[cyan]RESUMING[/cyan] from previous run (ID: {existing_state.setup_id[:8]}...)\n"
                    f"Completed steps: {', '.join(existing_state.get_completed_steps()) or 'none'}"
                ))
            else:
                # Start fresh
                self._state_manager.clear_state()
        elif not self._resume and self._state_manager.has_existing_state():
            # Clear old state if not resuming
            self._state_manager.clear_state()

        try:
            # Mark setup as started
            if not dry_run:
                self._state_manager.start_setup()

            # Step 1: Validate configuration
            results["validate"] = self._run_step_with_state("validate", self._step_validate)
            if results["validate"].status == StepStatus.FAILED:
                self._state_manager.complete_setup(success=False)
                return results

            if dry_run:
                return self._dry_run_summary()

            # Step 2: Create Lakehouse
            if self.config.resources.lakehouse.enabled:
                results["create_lakehouse"] = self._run_step_with_state(
                    "create_lakehouse", self._step_create_lakehouse
                )
                if results["create_lakehouse"].status == StepStatus.FAILED:
                    self._state_manager.complete_setup(success=False)
                    return results

            # Step 3: Upload CSV files
            if self.state.lakehouse_id:
                results["upload_files"] = self._run_step_with_state(
                    "upload_files", self._step_upload_lakehouse_files
                )

            # Step 4: Load tables
            if self.state.lakehouse_id:
                results["load_tables"] = self._run_step_with_state(
                    "load_tables", self._step_load_tables
                )

            # Step 5: Create Eventhouse
            if self.config.resources.eventhouse.enabled:
                results["create_eventhouse"] = self._run_step_with_state(
                    "create_eventhouse", self._step_create_eventhouse
                )

            # Step 6: Ingest Eventhouse data
            if self.state.eventhouse_id:
                results["ingest_data"] = self._run_step_with_state(
                    "ingest_data", self._step_ingest_eventhouse_data
                )

            # Step 7: Create Ontology
            if self.config.resources.ontology.enabled:
                results["create_ontology"] = self._run_step_with_state(
                    "create_ontology", self._step_create_ontology
                )

            # Step 8: Configure bindings
            if self.state.ontology_id:
                results["configure_bindings"] = self._run_step_with_state(
                    "configure_bindings", self._step_configure_bindings
                )

            # Step 9: Verify setup
            results["verify"] = self._run_step_with_state("verify", self._step_verify_setup)

            # Step 10: Refresh graph (if ontology was created and bindings configured)
            if self.state.ontology_id and self.state.bindings_configured:
                results["refresh_graph"] = self._run_step_with_state(
                    "refresh_graph", self._step_refresh_graph
                )

            # Mark setup as completed
            self._state_manager.complete_setup(success=True)

        except CancellationRequestedError:
            self._state_manager.cancel_setup()
            results["cancelled"] = StepResult(
                status=StepStatus.FAILED,
                message="Setup cancelled by user",
            )
        except Exception as e:
            logger.exception("Setup failed with unexpected error")
            self._state_manager.complete_setup(success=False)
            results["error"] = StepResult(
                status=StepStatus.FAILED,
                message=str(e),
                error=e,
            )
        finally:
            self._cleanup_clients()

        return results

    def run_single_step(self, step_name: str) -> StepResult:
        """
        Execute a single setup step independently.
        
        This method allows running any step on its own, useful for:
        - Re-running a failed step
        - Testing individual steps
        - Manual step-by-step setup
        
        Args:
            step_name: Name of the step to run (e.g., 'create_lakehouse', 'bind_static')
            
        Returns:
            StepResult with status, message, and any artifacts created
        """
        # Map step names to their implementation methods
        step_methods = {
            "validate": self._step_validate,
            "create_lakehouse": self._step_create_lakehouse,
            "upload_files": self._step_upload_lakehouse_files,
            "load_tables": self._step_load_tables,
            "create_eventhouse": self._step_create_eventhouse,
            "ingest_data": self._step_ingest_eventhouse_data,
            "create_ontology": self._step_create_ontology,
            "configure_bindings": self._step_configure_bindings,
            "bind_static": self._step_bind_static,
            "bind_timeseries": self._step_bind_timeseries,
            "bind_relationships": self._step_bind_relationships,
            "verify": self._step_verify_setup,
            "refresh_graph": self._step_refresh_graph,
        }
        
        if step_name not in step_methods:
            return StepResult(
                status=StepStatus.FAILED,
                message=f"Unknown step: {step_name}. Valid steps: {', '.join(step_methods.keys())}",
            )
        
        # Load existing state to restore resource IDs
        if self._state_manager.has_existing_state():
            existing_state = self._state_manager.load_state()
            if existing_state:
                self._handle_resume(existing_state)
        
        # Mark setup as in progress if not already
        if not self._state_manager.has_existing_state():
            self._state_manager.start_setup()
        
        try:
            # Run the step
            step_func = step_methods[step_name]
            result = self._run_step_with_state(step_name, step_func, force=True)
            
            return result
            
        except Exception as e:
            logger.exception(f"Step {step_name} failed with error")
            return StepResult(
                status=StepStatus.FAILED,
                message=str(e),
                error=e,
            )
        finally:
            self._cleanup_clients()

    def _run_step_with_state(
        self,
        step_name: str,
        step_func: Callable[[], StepResult],
        force: bool = False,
    ) -> StepResult:
        """
        Run a step with state persistence.
        
        Skips if already completed (resume mode) unless force=True.
        
        Args:
            step_name: Name of the step
            step_func: Function that executes the step
            force: If True, run even if already completed
        """
        # Check if already completed (resume mode) - skip unless forced
        if not force and self._state_manager.is_step_completed(step_name):
            artifact_id = self._state_manager.get_step_artifact_id(step_name)
            logger.info(f"Skipping completed step: {step_name}")
            return StepResult(
                status=StepStatus.SKIPPED,
                message=f"Already completed (resumed)",
                artifact_id=artifact_id,
            )

        # Mark step as started
        self._state_manager.start_step(step_name)

        try:
            result = step_func()

            # Update state based on result
            if result.status == StepStatus.COMPLETED:
                self._state_manager.complete_step(
                    step_name,
                    artifact_id=result.artifact_id,
                    artifact_name=result.artifact_name,
                    details=result.details,
                )
            elif result.status == StepStatus.SKIPPED:
                self._state_manager.skip_step(
                    step_name,
                    artifact_id=result.artifact_id,
                    artifact_name=result.artifact_name,
                    reason=result.message,
                )
            elif result.status == StepStatus.FAILED:
                self._state_manager.fail_step(step_name, result.message)

            # Update resource IDs in persistent state
            self._state_manager.update_resource_ids(
                lakehouse_id=self.state.lakehouse_id,
                lakehouse_name=self.state.lakehouse_name,
                eventhouse_id=self.state.eventhouse_id,
                eventhouse_name=self.state.eventhouse_name,
                kql_database_id=self.state.kql_database_id,
                kql_database_name=self.state.kql_database_name,
                ontology_id=self.state.ontology_id,
                ontology_name=self.state.ontology_name,
            )

            return result

        except Exception as e:
            self._state_manager.fail_step(step_name, str(e))
            raise

    def _handle_resume(self, existing_state) -> None:
        """Restore state from previous run."""
        # Restore resource IDs
        if existing_state.lakehouse_id:
            self.state.lakehouse_id = existing_state.lakehouse_id
            self.state.lakehouse_name = existing_state.lakehouse_name
        if existing_state.eventhouse_id:
            self.state.eventhouse_id = existing_state.eventhouse_id
            self.state.eventhouse_name = existing_state.eventhouse_name
        if existing_state.kql_database_id:
            self.state.kql_database_id = existing_state.kql_database_id
            self.state.kql_database_name = existing_state.kql_database_name
        if existing_state.ontology_id:
            self.state.ontology_id = existing_state.ontology_id
            self.state.ontology_name = existing_state.ontology_name

    def has_resumable_state(self) -> bool:
        """Check if there's a resumable state from a previous run."""
        if self._state_manager.has_existing_state():
            existing = self._state_manager.load_state()
            return existing is not None and existing.can_resume()
        return False

    def get_resume_summary(self) -> Optional[Dict[str, Any]]:
        """Get summary of resumable state, if any."""
        if self._state_manager.has_existing_state():
            self._state_manager.load_state()
            return self._state_manager.get_resume_summary()
        return None

    def clear_state(self) -> None:
        """Clear any existing state file."""
        self._state_manager.clear_state()

    def _step_validate(self) -> StepResult:
        """Validate configuration."""
        start = time.time()
        self._report_progress("validate", "in_progress", 0)

        errors = self.config.validate()
        if errors:
            return StepResult(
                status=StepStatus.FAILED,
                message=f"Validation failed: {'; '.join(errors)}",
                duration_seconds=time.time() - start,
            )

        self._report_progress("validate", "completed", 100)
        return StepResult(
            status=StepStatus.COMPLETED,
            message="Configuration validated successfully",
            duration_seconds=time.time() - start,
        )

    def _step_create_lakehouse(self) -> StepResult:
        """Create Lakehouse."""
        start = time.time()
        self._check_cancellation()
        self._report_progress("create_lakehouse", "in_progress", 0)

        name = self.config.resources.lakehouse.name

        # Check if lakehouse already exists
        existing = self.fabric_client.find_lakehouse_by_name(name)
        if existing:
            existing_id = existing.get("id")
            should_skip, message = self._handle_existing_resource(
                resource_type="Lakehouse",
                resource_name=name,
                existing_id=existing_id,
            )
            if should_skip:
                self.state.lakehouse_id = existing_id
                self.state.lakehouse_name = name
                self._report_progress("create_lakehouse", "completed", 100)
                return StepResult(
                    status=StepStatus.SKIPPED,
                    message=message,
                    artifact_id=existing_id,
                    artifact_name=name,
                    duration_seconds=time.time() - start,
                )

        # Create new lakehouse
        result = self.lakehouse_client.create_lakehouse(
            display_name=name,
            description=self.config.resources.lakehouse.description,
            skip_if_exists=False,  # We've already handled existing check
        )

        self.state.lakehouse_id = result.get("id")
        self.state.lakehouse_name = result.get("displayName")

        self._report_progress("create_lakehouse", "completed", 100)
        return StepResult(
            status=StepStatus.COMPLETED,
            message=f"Lakehouse created: {name}",
            artifact_id=self.state.lakehouse_id,
            artifact_name=self.state.lakehouse_name,
            duration_seconds=time.time() - start,
        )

    def _get_existing_lakehouse_tables(self) -> set:
        """Get set of existing table names in the lakehouse."""
        if not self.state.lakehouse_id:
            return set()
        try:
            tables = self.lakehouse_client.list_tables(self.state.lakehouse_id)
            return {t.get("name", "") for t in tables}
        except Exception as e:
            logger.warning(f"Could not list lakehouse tables: {e}")
            return set()

    def _get_existing_eventhouse_tables(self) -> set:
        """Get set of existing table names in the eventhouse KQL database."""
        if not self.state.eventhouse_id or not self.state.kql_database_name:
            return set()
        try:
            # Use list_tables which uses management endpoint for control commands
            tables = self.eventhouse_client.list_tables(
                eventhouse_id=self.state.eventhouse_id,
                database_name=self.state.kql_database_name,
            )
            return set(tables)
        except Exception as e:
            logger.warning(f"Could not list eventhouse tables: {e}")
            return set()

    def _step_upload_lakehouse_files(self) -> StepResult:
        """Upload CSV files to Lakehouse (skip if tables already exist)."""
        start = time.time()
        self._check_cancellation()
        self._report_progress("upload_files", "in_progress", 0)

        csv_files = self.config.get_lakehouse_csv_files()
        if not csv_files:
            return StepResult(
                status=StepStatus.SKIPPED,
                message="No CSV files to upload",
                duration_seconds=time.time() - start,
            )

        # Check which tables already exist - if tables exist, files were already processed
        existing_tables = self._get_existing_lakehouse_tables()
        expected_tables = {f.stem for f in csv_files}
        
        if expected_tables.issubset(existing_tables):
            logger.info(f"All {len(expected_tables)} tables already exist in lakehouse, skipping upload")
            self.state.uploaded_files.extend([f.name for f in csv_files])
            return StepResult(
                status=StepStatus.SKIPPED,
                message=f"All {len(expected_tables)} tables already exist in lakehouse",
                duration_seconds=time.time() - start,
                details={"existing_tables": list(existing_tables & expected_tables)},
            )

        uploaded = []
        failed = []
        skipped = []

        for i, csv_file in enumerate(csv_files):
            self._check_cancellation()
            progress = (i / len(csv_files)) * 100
            self._report_progress("upload_files", "in_progress", progress)

            # Skip if table already exists
            if csv_file.stem in existing_tables:
                logger.info(f"Table {csv_file.stem} already exists, skipping upload of {csv_file.name}")
                skipped.append(csv_file.name)
                self.state.uploaded_files.append(csv_file.name)
                continue

            try:
                self.onelake_client.upload_file(
                    item_id=self.state.lakehouse_id,
                    local_file=csv_file,
                    remote_path=csv_file.name,
                    item_name=self.state.lakehouse_name,
                )
                uploaded.append(csv_file.name)
                self.state.uploaded_files.append(csv_file.name)
            except Exception as e:
                logger.error(f"Failed to upload {csv_file.name}: {e}")
                failed.append(csv_file.name)

        self._report_progress("upload_files", "completed", 100)

        if failed:
            return StepResult(
                status=StepStatus.FAILED,
                message=f"Uploaded {len(uploaded)} files, {len(failed)} failed, {len(skipped)} skipped",
                duration_seconds=time.time() - start,
                details={"uploaded": uploaded, "failed": failed, "skipped": skipped},
            )

        return StepResult(
            status=StepStatus.COMPLETED,
            message=f"Uploaded {len(uploaded)} files, {len(skipped)} skipped (already exist)",
            duration_seconds=time.time() - start,
            details={"uploaded": uploaded, "skipped": skipped},
        )

    def _step_load_tables(self) -> StepResult:
        """Load CSV files to Delta tables (skip if tables already exist)."""
        start = time.time()
        self._check_cancellation()
        self._report_progress("load_tables", "in_progress", 0)

        csv_files = [f for f in self.state.uploaded_files if f.endswith(".csv")]
        if not csv_files:
            return StepResult(
                status=StepStatus.SKIPPED,
                message="No CSV files to load",
                duration_seconds=time.time() - start,
            )

        # Check which tables already exist
        existing_tables = self._get_existing_lakehouse_tables()
        expected_tables = {Path(f).stem for f in csv_files}
        
        # If all tables exist, skip entirely
        if expected_tables.issubset(existing_tables):
            logger.info(f"All {len(expected_tables)} tables already exist, skipping load")
            self.state.loaded_tables.extend(list(expected_tables))
            return StepResult(
                status=StepStatus.SKIPPED,
                message=f"All {len(expected_tables)} tables already exist in lakehouse",
                duration_seconds=time.time() - start,
                details={"existing_tables": list(expected_tables)},
            )

        # Filter to only load files for tables that don't exist
        files_to_load = [f for f in csv_files if Path(f).stem not in existing_tables]
        skipped_tables = [Path(f).stem for f in csv_files if Path(f).stem in existing_tables]
        
        if skipped_tables:
            logger.info(f"Skipping {len(skipped_tables)} tables that already exist: {skipped_tables}")
            self.state.loaded_tables.extend(skipped_tables)

        if not files_to_load:
            return StepResult(
                status=StepStatus.SKIPPED,
                message=f"All tables already exist",
                duration_seconds=time.time() - start,
                details={"skipped": skipped_tables},
            )

        results = self.lakehouse_client.load_all_csv_files(
            lakehouse_id=self.state.lakehouse_id,
            csv_files=files_to_load,
        )

        loaded = [name for name, r in results.items() if r["status"] == "success"]
        failed = [name for name, r in results.items() if r["status"] == "failed"]

        self.state.loaded_tables.extend(loaded)
        self._report_progress("load_tables", "completed", 100)

        if failed:
            return StepResult(
                status=StepStatus.FAILED,
                message=f"Loaded {len(loaded)} tables, {len(failed)} failed, {len(skipped_tables)} skipped",
                duration_seconds=time.time() - start,
                details={"loaded": loaded, "failed": failed, "skipped": skipped_tables},
            )

        return StepResult(
            status=StepStatus.COMPLETED,
            message=f"Loaded {len(loaded)} tables, {len(skipped_tables)} skipped (already exist)",
            duration_seconds=time.time() - start,
            details={"loaded": loaded, "skipped": skipped_tables},
        )

    def _step_create_eventhouse(self) -> StepResult:
        """Create Eventhouse."""
        start = time.time()
        self._check_cancellation()
        self._report_progress("create_eventhouse", "in_progress", 0)

        name = self.config.resources.eventhouse.name

        # Check if eventhouse already exists
        existing = self.fabric_client.find_eventhouse_by_name(name)
        if existing:
            existing_id = existing.get("id")
            should_skip, message = self._handle_existing_resource(
                resource_type="Eventhouse",
                resource_name=name,
                existing_id=existing_id,
            )
            if should_skip:
                self.state.eventhouse_id = existing_id
                self.state.eventhouse_name = name

                # Get default KQL database for existing eventhouse
                kql_db = self.eventhouse_client.get_default_database_for_eventhouse(existing_id)
                if kql_db:
                    self.state.kql_database_id = kql_db.get("id")
                    self.state.kql_database_name = kql_db.get("displayName")

                self._report_progress("create_eventhouse", "completed", 100)
                return StepResult(
                    status=StepStatus.SKIPPED,
                    message=message,
                    artifact_id=existing_id,
                    artifact_name=name,
                    duration_seconds=time.time() - start,
                )

        # Create new eventhouse
        result = self.eventhouse_client.create_eventhouse(
            display_name=name,
            description=self.config.resources.eventhouse.description,
            skip_if_exists=False,  # We've already handled existing check
        )

        self.state.eventhouse_id = result.get("id")
        self.state.eventhouse_name = result.get("displayName")

        # Get default KQL database
        kql_db = self.eventhouse_client.get_default_database_for_eventhouse(
            self.state.eventhouse_id
        )
        if kql_db:
            self.state.kql_database_id = kql_db.get("id")
            self.state.kql_database_name = kql_db.get("displayName")

        self._report_progress("create_eventhouse", "completed", 100)
        return StepResult(
            status=StepStatus.COMPLETED,
            message=f"Eventhouse created: {name}",
            artifact_id=self.state.eventhouse_id,
            artifact_name=self.state.eventhouse_name,
            duration_seconds=time.time() - start,
        )

    def _step_ingest_eventhouse_data(self) -> StepResult:
        """
        Ingest data into Eventhouse KQL database (skip tables that already have data).
        
        This step:
        1. Parses bindings.yaml to get KQL table schemas
        2. Creates tables in the KQL database (if not exist)
        3. Uploads CSV files to Lakehouse Files area (for OneLake access)
        4. Ingests data from OneLake into KQL tables (if tables are empty)
        """
        start = time.time()
        self._check_cancellation()
        self._report_progress("ingest_data", "in_progress", 0)

        csv_files = self.config.get_eventhouse_csv_files()
        if not csv_files:
            return StepResult(
                status=StepStatus.SKIPPED,
                message="No Eventhouse data files to ingest",
                duration_seconds=time.time() - start,
            )

        # Get table configurations from bindings.yaml
        table_configs = get_eventhouse_table_configs(self.config.demo_path)
        if not table_configs:
            logger.warning("No eventhouse table configs found in bindings.yaml, inferring from CSV")
            # Fallback: we'll create basic configs from CSV headers
            table_configs = self._infer_eventhouse_tables_from_csv(csv_files)

        if not table_configs:
            return StepResult(
                status=StepStatus.SKIPPED,
                message="No Eventhouse table configurations found",
                duration_seconds=time.time() - start,
            )

        # Get the KQL database for this eventhouse
        if not self.state.kql_database_id or not self.state.kql_database_name:
            # Try to get the default database
            kql_db = self.eventhouse_client.get_default_database_for_eventhouse(
                self.state.eventhouse_id
            )
            if kql_db:
                self.state.kql_database_id = kql_db.get("id")
                self.state.kql_database_name = kql_db.get("displayName")
            else:
                return StepResult(
                    status=StepStatus.FAILED,
                    message="Could not find KQL database for Eventhouse",
                    duration_seconds=time.time() - start,
                )

        # Check which tables already exist (existence = ingestion was at least attempted)
        # KQL async ingestion means tables may have 0 rows while still processing
        existing_tables = set(self._get_existing_eventhouse_tables())
        tables_with_data = {}
        for table_name in existing_tables:
            try:
                count = self.eventhouse_client.get_table_count(
                    eventhouse_id=self.state.eventhouse_id,
                    database_name=self.state.kql_database_name,
                    table_name=table_name,
                )
                tables_with_data[table_name] = count
            except Exception:
                tables_with_data[table_name] = 0  # Table exists but couldn't get count

        expected_tables = {tc.table_name for tc in table_configs}
        
        # Tables to skip: those that already exist (ingestion was initiated, possibly still async)
        # Table existence is the key check - if table exists, .create table and .ingest were called
        tables_to_skip = existing_tables & expected_tables
        
        # If all expected tables already exist, skip entirely (async ingestion may still be processing)
        if expected_tables.issubset(tables_to_skip):
            tables_info = {t: tables_with_data.get(t, 0) for t in expected_tables}
            logger.info(f"All {len(expected_tables)} eventhouse tables already exist, skipping ingestion (async may still be processing)")
            return StepResult(
                status=StepStatus.SKIPPED,
                message=f"All {len(expected_tables)} eventhouse tables already exist (async ingestion may still be processing)",
                duration_seconds=time.time() - start,
                details={"existing_tables": tables_info},
            )

        total_tables = len(table_configs)
        ingested_tables = []
        skipped_tables = []
        failed_tables = []

        for i, table_config in enumerate(table_configs):
            self._check_cancellation()
            progress_pct = int((i / total_tables) * 100)
            self._report_progress("ingest_data", "in_progress", progress_pct)

            table_name = table_config.table_name
            logger.info(f"Processing table: {table_name}")

            # Check if table already exists (ingestion was initiated - async may still be processing)
            if table_name in existing_tables:
                row_count = tables_with_data.get(table_name, 0)
                status_msg = f"has {row_count} rows" if row_count > 0 else "exists (async ingestion may still be processing)"
                logger.info(f"Table {table_name} {status_msg}, skipping")
                skipped_tables.append(table_name)
                continue

            # Find matching CSV file
            csv_file = self._find_csv_for_table(csv_files, table_name)
            if not csv_file:
                logger.warning(f"No CSV file found for table {table_name}")
                failed_tables.append(table_name)
                continue

            try:
                # Step 1: Create the KQL table with schema (use .create-merge which is idempotent)
                logger.info(f"Creating/updating KQL table: {table_name}")
                create_cmd = table_config.to_kql_schema()
                self.eventhouse_client.execute_kql_management(
                    eventhouse_id=self.state.eventhouse_id,
                    database_name=self.state.kql_database_name,
                    command=create_cmd,
                )

                # Step 2: Upload CSV to Lakehouse Files area for OneLake access
                # KQL can ingest from OneLake paths
                if self.state.lakehouse_id:
                    logger.info(f"Uploading {csv_file.name} to Lakehouse for OneLake access")
                    eventhouse_folder = "eventhouse"  # Upload to a separate folder
                    
                    # Upload to Lakehouse/Files/eventhouse/{file}.csv
                    self.onelake_client.upload_file(
                        item_id=self.state.lakehouse_id,
                        local_file=csv_file,
                        remote_path=f"{eventhouse_folder}/{csv_file.name}",
                        item_name=self.state.lakehouse_name,
                        item_type="Lakehouse",
                        folder="Files",
                    )

                    # Step 3: Ingest from OneLake
                    # OneLake path format: https://onelake.dfs.fabric.microsoft.com/{workspace_id}/{item_id}/Files/eventhouse/{file}.csv
                    # The ;impersonate suffix tells KQL to use the caller's identity to access OneLake
                    onelake_path = (
                        f"https://onelake.dfs.fabric.microsoft.com/"
                        f"{self.config.fabric.workspace_id}/"
                        f"{self.state.lakehouse_id}/"
                        f"Files/{eventhouse_folder}/{csv_file.name};impersonate"
                    )

                    logger.info(f"Ingesting data into {table_name} from OneLake")
                    self.eventhouse_client.ingest_from_onelake(
                        eventhouse_id=self.state.eventhouse_id,
                        database_name=self.state.kql_database_name,
                        table_name=table_name,
                        onelake_path=onelake_path,
                        file_format="csv",
                        ignore_first_record=True,  # Skip CSV header
                    )

                    # Wait for async ingestion to complete (KQL ingestion is async)
                    # Use exponential backoff: 2s, 4s, 8s, 16s, 32s = ~62s total
                    row_count = 0
                    wait_time = 2
                    max_attempts = 6
                    for attempt in range(max_attempts):
                        time.sleep(wait_time)
                        row_count = self.eventhouse_client.get_table_count(
                            eventhouse_id=self.state.eventhouse_id,
                            database_name=self.state.kql_database_name,
                            table_name=table_name,
                        )
                        if row_count > 0:
                            break
                        logger.debug(f"Waiting for {table_name} ingestion (attempt {attempt + 1}/{max_attempts}, next wait: {wait_time * 2}s)")
                        wait_time = min(wait_time * 2, 30)  # Cap at 30s
                    
                    if row_count > 0:
                        logger.info(f"Table {table_name} now has {row_count} rows")
                    else:
                        logger.warning(f"Table {table_name} still shows 0 rows (async ingestion may still be processing)")

                ingested_tables.append(table_name)

            except Exception as e:
                logger.error(f"Failed to ingest table {table_name}: {e}")
                failed_tables.append(table_name)

        self._report_progress("ingest_data", "completed", 100)

        if failed_tables:
            if ingested_tables or skipped_tables:
                return StepResult(
                    status=StepStatus.COMPLETED,
                    message=f"Ingested {len(ingested_tables)} tables, {len(skipped_tables)} skipped, {len(failed_tables)} failed: {', '.join(failed_tables)}",
                    duration_seconds=time.time() - start,
                    details={
                        "ingested_tables": ingested_tables,
                        "skipped_tables": skipped_tables,
                        "failed_tables": failed_tables,
                    },
                )
            else:
                return StepResult(
                    status=StepStatus.FAILED,
                    message=f"All {len(failed_tables)} tables failed to ingest",
                    duration_seconds=time.time() - start,
                    details={"failed_tables": failed_tables},
                )

        return StepResult(
            status=StepStatus.COMPLETED,
            message=f"Ingested {len(ingested_tables)} tables, {len(skipped_tables)} skipped (already have data)",
            duration_seconds=time.time() - start,
            details={"ingested_tables": ingested_tables},
        )

    def _find_csv_for_table(self, csv_files: List[Path], table_name: str) -> Optional[Path]:
        """Find the CSV file matching a table name."""
        # Exact match first
        for csv_file in csv_files:
            if csv_file.stem == table_name:
                return csv_file
        
        # Case-insensitive match
        table_lower = table_name.lower()
        for csv_file in csv_files:
            if csv_file.stem.lower() == table_lower:
                return csv_file
        
        return None

    def _infer_eventhouse_tables_from_csv(self, csv_files: List[Path]) -> List:
        """
        Infer table configurations from CSV headers when bindings.yaml is not available.
        
        This is a fallback mechanism for demos that don't have the structured
        bindings.yaml file.
        """
        from .binding.yaml_parser import EventhouseTableConfig
        import csv
        
        configs = []
        
        for csv_file in csv_files:
            try:
                with open(csv_file, "r", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    headers = next(reader)
                
                if not headers:
                    continue
                
                # Infer column types from headers
                columns = []
                key_column = None
                timestamp_column = None
                
                for header in headers:
                    header_lower = header.lower()
                    
                    # Guess type from column name
                    if header_lower in ("timestamp", "time", "datetime", "precisetimestamp"):
                        col_type = "datetime"
                        if not timestamp_column:
                            timestamp_column = header
                    elif header_lower.endswith("id") or header_lower == "key":
                        col_type = "string"
                        if not key_column:
                            key_column = header
                    elif any(kw in header_lower for kw in ("count", "qty", "quantity", "num")):
                        col_type = "int"
                    elif any(kw in header_lower for kw in ("temp", "pressure", "humidity", "speed", "pct", "percent", "rate")):
                        col_type = "real"
                    elif header_lower in ("true", "false", "is", "has", "enabled", "active"):
                        col_type = "bool"
                    else:
                        col_type = "string"
                    
                    columns.append({"name": header, "type": col_type})
                
                # Default key column to first ID-like column or first column
                if not key_column and headers:
                    key_column = headers[0]
                
                # Default timestamp to "Timestamp" if exists
                if not timestamp_column:
                    timestamp_column = "Timestamp"
                
                config = EventhouseTableConfig(
                    entity_name=csv_file.stem,
                    table_name=csv_file.stem,
                    key_column=key_column,
                    timestamp_column=timestamp_column,
                    row_count=0,
                    columns=columns,
                )
                configs.append(config)
                
            except Exception as e:
                logger.warning(f"Failed to infer schema from {csv_file}: {e}")
        
        return configs

    def _validate_ontology_definition_with_sdk(
        self, 
        ttl_path: Path,
        strict: bool = False,
    ) -> tuple[bool, list[str], list[str]]:
        """
        Pre-flight validation of ontology definition using SDK OntologyValidator.
        
        Phase 4: Uses SDK's OntologyValidator for comprehensive validation
        before making API calls. This catches issues early and provides
        better error messages than API failures.
        
        Args:
            ttl_path: Path to the TTL file to validate
            strict: If True, treat warnings as errors
            
        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        errors = []
        warnings = []
        
        try:
            # Convert TTL to SDK builder/definition
            from .ontology.sdk_converter import ttl_to_sdk_builder
            
            builder = ttl_to_sdk_builder(str(ttl_path))
            definition = builder.build()
            
            # Use SDK OntologyValidator for comprehensive validation
            validator = SDKOntologyValidator(strict=strict)
            
            try:
                is_valid = validator.validate(definition)
                warnings = validator.get_warnings()
                
                if warnings:
                    for warning in warnings:
                        logger.warning(f"SDK validation warning: {warning}")
                
                return is_valid, [], warnings
                
            except SDKValidationError as e:
                # Strict mode: validation errors raise exception
                errors = e.details.get("errors", [str(e)]) if e.details else [str(e)]
                warnings = e.details.get("warnings", []) if e.details else []
                
                for error in errors:
                    logger.error(f"SDK validation error: {error}")
                
                return False, errors, warnings
                
        except Exception as e:
            # Conversion or other error
            logger.warning(f"SDK pre-flight validation failed: {e}")
            errors.append(f"Pre-flight validation error: {e}")
            return False, errors, warnings

    def _step_create_ontology(self) -> StepResult:
        """Create Ontology from TTL file and upload definition."""
        start = time.time()
        self._check_cancellation()
        self._report_progress("create_ontology", "in_progress", 0)

        name = self.config.resources.ontology.name

        # Find TTL file in ontology folder
        ontology_folder = self.config.demo_path / "ontology"
        ttl_files = list(ontology_folder.glob("*.ttl"))
        
        if not ttl_files:
            return StepResult(
                status=StepStatus.FAILED,
                message=f"No TTL files found in {ontology_folder}",
                duration_seconds=time.time() - start,
            )
        
        ttl_file = ttl_files[0]  # Use first TTL file found
        logger.info(f"Using TTL file: {ttl_file}")

        # Check if ontology already exists
        existing = self.fabric_client.find_ontology_by_name(name)
        if existing:
            existing_id = existing.get("id")
            should_skip, message = self._handle_existing_resource(
                resource_type="Ontology",
                resource_name=name,
                existing_id=existing_id,
            )
            if should_skip:
                self.state.ontology_id = existing_id
                self.state.ontology_name = name
                self._report_progress("create_ontology", "completed", 100)
                return StepResult(
                    status=StepStatus.SKIPPED,
                    message=message,
                    artifact_id=existing_id,
                    artifact_name=name,
                    duration_seconds=time.time() - start,
                )

        # Parse TTL file to get Fabric definition
        self._report_progress("create_ontology", "in_progress", 20)
        try:
            definition, extracted_name = parse_ttl_file(str(ttl_file))
            entity_count = len([p for p in definition.get("parts", []) if "EntityTypes" in p.get("path", "")])
            rel_count = len([p for p in definition.get("parts", []) if "RelationshipTypes" in p.get("path", "")])
            logger.info(f"Parsed TTL: {entity_count} entity types, {rel_count} relationship types")
        except Exception as e:
            logger.error(f"Failed to parse TTL file: {e}")
            return StepResult(
                status=StepStatus.FAILED,
                message=f"Failed to parse TTL file: {e}",
                error=e,
                duration_seconds=time.time() - start,
            )

        # Phase 4: SDK Pre-flight Validation
        # Validate ontology definition with SDK before making API calls
        self._report_progress("create_ontology", "in_progress", 30)
        is_valid, sdk_errors, sdk_warnings = self._validate_ontology_definition_with_sdk(
            ttl_path=ttl_file,
            strict=False,  # Don't fail on warnings, just log them
        )
        
        if not is_valid and sdk_errors:
            # Log all errors but only fail if there are critical ones
            for error in sdk_errors:
                logger.error(f"SDK validation: {error}")
            
            # Check if these are critical errors that would cause API failure
            critical_errors = [e for e in sdk_errors if "must" in e.lower() or "invalid" in e.lower() or "duplicate" in e.lower()]
            
            if critical_errors:
                return StepResult(
                    status=StepStatus.FAILED,
                    message=f"Ontology validation failed: {critical_errors[0]}",
                    error=DemoAutomationError(f"SDK validation failed: {'; '.join(critical_errors)}"),
                    duration_seconds=time.time() - start,
                    details={
                        "validation_errors": sdk_errors,
                        "validation_warnings": sdk_warnings,
                    }
                )
            else:
                # Non-critical errors, proceed with warning
                logger.warning(f"SDK validation issues found but proceeding: {sdk_errors}")
        
        # Log any warnings from SDK validation
        for warning in sdk_warnings:
            logger.warning(f"SDK validation warning: {warning}")

        # Create new ontology (empty shell)
        self._report_progress("create_ontology", "in_progress", 40)
        try:
            result = self.fabric_client.create_ontology(
                display_name=name,
                description=self.config.resources.ontology.description,
            )
            self.state.ontology_id = result.get("id")
            self.state.ontology_name = result.get("displayName")
            logger.info(f"Created ontology: {name} (ID: {self.state.ontology_id})")
        except Exception as e:
            logger.error(f"Failed to create ontology: {e}")
            return StepResult(
                status=StepStatus.FAILED,
                message=f"Failed to create ontology: {e}",
                error=e,
                duration_seconds=time.time() - start,
            )

        # Upload the ontology definition
        self._report_progress("create_ontology", "in_progress", 60)
        try:
            self.fabric_client.update_ontology_definition(
                ontology_id=self.state.ontology_id,
                definition=definition,
            )
            logger.info(f"Uploaded ontology definition with {entity_count} entities and {rel_count} relationships")
        except Exception as e:
            logger.error(f"Failed to upload ontology definition: {e}")
            # Clean up: delete the empty ontology we created
            try:
                self.fabric_client.delete_ontology(self.state.ontology_id)
            except Exception:
                pass
            return StepResult(
                status=StepStatus.FAILED,
                message=f"Failed to upload ontology definition: {e}",
                error=e,
                duration_seconds=time.time() - start,
            )

        self._report_progress("create_ontology", "completed", 100)
        return StepResult(
            status=StepStatus.COMPLETED,
            message=f"Ontology created with {entity_count} entities, {rel_count} relationships",
            artifact_id=self.state.ontology_id,
            artifact_name=self.state.ontology_name,
            duration_seconds=time.time() - start,
            details={
                "entity_count": entity_count,
                "relationship_count": rel_count,
                "ttl_file": str(ttl_file),
            }
        )

    def _step_configure_bindings(self) -> StepResult:
        """
        Configure ontology bindings for lakehouse and eventhouse data sources.
        
        This step:
        1. Parses bindings.yaml for entity and relationship bindings
        2. Gets the ontology definition to extract entity/relationship IDs
        3. Creates lakehouse (static) bindings for all lakehouse entities
        4. Creates eventhouse (timeseries) bindings for all eventhouse entities
        5. Creates relationship contextualizations
        6. Uploads the binding definition to Fabric via updateDefinition API
        7. Validates bindings were successfully created
        """
        import base64
        import json
        
        start = time.time()
        self._check_cancellation()
        self._report_progress("configure_bindings", "in_progress", 0)

        # Parse bindings.yaml (preferred) or fall back to markdown
        yaml_config = parse_bindings_yaml(self.config.demo_path)
        
        if not yaml_config:
            # Fall back to markdown parsing
            parsed_bindings = parse_demo_bindings(self.config.demo_path)
            if not parsed_bindings.get("static") and not parsed_bindings.get("timeseries"):
                return StepResult(
                    status=StepStatus.SKIPPED,
                    message="No binding configurations found",
                    duration_seconds=time.time() - start,
                )
            # Convert markdown format to yaml config for unified processing
            yaml_config = self._convert_markdown_to_yaml_config(parsed_bindings)

        self._report_progress("configure_bindings", "in_progress", 10)

        # Get ontology definition to extract entity/relationship type IDs
        try:
            ont_definition = self.fabric_client.get_ontology_definition(self.state.ontology_id)
        except Exception as e:
            logger.error(f"Failed to get ontology definition: {e}")
            return StepResult(
                status=StepStatus.FAILED,
                message=f"Failed to get ontology definition: {e}",
                error=e,
                duration_seconds=time.time() - start,
            )

        self._report_progress("configure_bindings", "in_progress", 20)

        # Build entity name -> ID mapping from ontology definition
        entity_name_to_id = {}
        entity_id_to_properties = {}  # entity_id -> {prop_name: prop_id}
        relationship_name_to_id = {}
        
        # Track existing binding IDs to reuse (prevents duplicate bindings)
        existing_entity_binding_ids = {}  # entity_id -> binding_id
        existing_rel_contextualization_ids = {}  # relationship_id -> contextualization_id
        
        # Debug: log ontology definition structure
        logger.debug(f"Ontology definition keys: {ont_definition.keys()}")
        
        parts = ont_definition.get("definition", {}).get("parts", [])
        if not parts:
            parts = ont_definition.get("parts", [])
        
        logger.debug(f"Found {len(parts)} parts in ontology definition")
        
        for part in parts:
            path = part.get("path", "")
            payload_b64 = part.get("payload", "")
            
            if not payload_b64:
                continue
            
            try:
                payload_json = base64.b64decode(payload_b64).decode("utf-8")
                payload = json.loads(payload_json)
            except Exception as e:
                logger.warning(f"Failed to decode payload for {path}: {e}")
                continue
            
            # Extract entity type mappings
            if "EntityTypes/" in path and "DataBindings" not in path:
                entity_id = payload.get("id", "")
                entity_name = payload.get("name", "")
                if entity_id and entity_name:
                    entity_name_to_id[entity_name] = entity_id
                    # Also store properties mapping
                    props = {}
                    for prop in payload.get("properties", []):
                        prop_name = prop.get("name", "")
                        prop_id = prop.get("id", "")
                        if prop_name and prop_id:
                            props[prop_name] = prop_id
                    entity_id_to_properties[entity_id] = props
                    logger.debug(f"Mapped entity: {entity_name} -> {entity_id} with {len(props)} properties")
            
            # Extract relationship type mappings
            elif "RelationshipTypes/" in path and "Contextualizations" not in path:
                rel_id = payload.get("id", "")
                rel_name = payload.get("name", "")
                if rel_id and rel_name:
                    relationship_name_to_id[rel_name] = rel_id
                    logger.debug(f"Mapped relationship: {rel_name} -> {rel_id}")
            
            # Extract existing binding IDs (to reuse and avoid duplicates)
            # Path format: EntityTypes/{entity_id}/DataBindings/{binding_id}.json
            elif "/DataBindings/" in path:
                parts_split = path.split("/")
                # Expected: ['EntityTypes', 'entity_id', 'DataBindings', 'binding_id.json']
                if len(parts_split) >= 4:
                    entity_id = parts_split[1]
                    binding_file = parts_split[3]  # e.g., "uuid.json"
                    binding_id = binding_file.replace(".json", "")
                    existing_entity_binding_ids[entity_id] = binding_id
                    logger.info(f"Found existing binding for entity {entity_id}: {binding_id}")
            
            # Extract existing contextualization IDs
            # Path format: RelationshipTypes/{rel_id}/Contextualizations/{ctx_id}.json
            elif "/Contextualizations/" in path:
                parts_split = path.split("/")
                # Expected: ['RelationshipTypes', 'rel_id', 'Contextualizations', 'ctx_id.json']
                if len(parts_split) >= 4:
                    rel_id = parts_split[1]
                    ctx_file = parts_split[3]  # e.g., "uuid.json"
                    ctx_id = ctx_file.replace(".json", "")
                    existing_rel_contextualization_ids[rel_id] = ctx_id
                    logger.info(f"Found existing contextualization for relationship {rel_id}: {ctx_id}")

        logger.info(f"Found {len(entity_name_to_id)} entities and {len(relationship_name_to_id)} relationships in ontology")
        logger.info(f"Found {len(existing_entity_binding_ids)} existing entity bindings, {len(existing_rel_contextualization_ids)} existing contextualizations")

        self._report_progress("configure_bindings", "in_progress", 30)

        # Build bindings
        builder = OntologyBindingBuilder(
            workspace_id=self.config.fabric.workspace_id,
            ontology_id=self.state.ontology_id,
        )

        lakehouse_binding_count = 0
        eventhouse_binding_count = 0
        relationship_binding_count = 0

        # --- Add Lakehouse (static) bindings ---
        if self.state.lakehouse_id and yaml_config.lakehouse_entities:
            for entity_binding in yaml_config.lakehouse_entities:
                entity_name = entity_binding.entity_name
                entity_id = entity_name_to_id.get(entity_name)
                
                if not entity_id:
                    logger.warning(f"No entity ID found for '{entity_name}', skipping binding")
                    continue
                
                # Get property mappings using entity property IDs
                # Only include properties that have valid IDs in the ontology
                entity_props = entity_id_to_properties.get(entity_id, {})
                property_mappings = {}
                skipped_props = []
                
                for pm in entity_binding.property_mappings:
                    source_col = pm.source_column
                    target_prop_name = pm.target_property
                    # Only use property ID if it exists in ontology
                    prop_id = entity_props.get(target_prop_name)
                    if prop_id:
                        property_mappings[source_col] = prop_id
                    else:
                        skipped_props.append(target_prop_name)
                
                if skipped_props:
                    logger.warning(f"Skipped {len(skipped_props)} properties for '{entity_name}' (not in ontology): {skipped_props[:3]}...")
                
                if not property_mappings:
                    logger.warning(f"No valid property mappings for '{entity_name}', skipping binding")
                    continue
                
                # Reuse existing binding ID if available (prevents duplicate bindings)
                existing_binding_id = existing_entity_binding_ids.get(entity_id)
                if existing_binding_id:
                    logger.info(f"Reusing existing binding ID for {entity_name} ({entity_id}): {existing_binding_id}")
                else:
                    logger.debug(f"No existing binding ID for {entity_name} ({entity_id}), will generate new UUID")
                
                builder.add_lakehouse_binding(
                    entity_type_id=entity_id,
                    lakehouse_id=self.state.lakehouse_id,
                    table_name=entity_binding.table_name,
                    key_column=entity_binding.key_column,
                    property_mappings=property_mappings,
                    binding_id=existing_binding_id,  # Reuse existing ID
                )
                
                # Register key property for relationship contextualizations
                key_prop_id = entity_props.get(entity_binding.key_column, entity_binding.key_column)
                builder.register_entity_key_property(entity_name, key_prop_id)
                
                lakehouse_binding_count += 1
                logger.info(f"Added lakehouse binding: {entity_name} -> {entity_binding.table_name}")

        self._report_progress("configure_bindings", "in_progress", 50)

        # --- Add Eventhouse (timeseries) bindings ---
        if self.state.eventhouse_id and self.state.kql_database_id and yaml_config.eventhouse_entities:
            # Get KQL database name
            try:
                kql_db = self.fabric_client.get_kql_database(self.state.kql_database_id)
                database_name = kql_db.get("displayName", self.config.resources.eventhouse.name)
            except Exception:
                database_name = self.config.resources.eventhouse.name
            
            for entity_binding in yaml_config.eventhouse_entities:
                entity_name = entity_binding.entity_name
                entity_id = entity_name_to_id.get(entity_name)
                
                if not entity_id:
                    logger.warning(f"No entity ID found for '{entity_name}', skipping eventhouse binding")
                    continue
                
                # Get property mappings - only include properties with valid IDs in ontology
                entity_props = entity_id_to_properties.get(entity_id, {})
                property_mappings = {}
                skipped_props = []
                
                for pm in entity_binding.property_mappings:
                    source_col = pm.source_column
                    target_prop_name = pm.target_property
                    prop_id = entity_props.get(target_prop_name)
                    if prop_id:
                        property_mappings[source_col] = prop_id
                    else:
                        skipped_props.append(target_prop_name)
                
                # Fabric API requires key property to be mapped in propertyBindings
                # even for TimeSeries bindings - add it if not already present
                key_col = entity_binding.key_column
                key_prop_id = entity_props.get(key_col)
                if key_prop_id and key_col not in property_mappings:
                    property_mappings[key_col] = key_prop_id
                    logger.debug(f"Added key property mapping: {key_col} -> {key_prop_id}")
                
                if skipped_props:
                    logger.warning(f"Skipped {len(skipped_props)} properties for '{entity_name}' (not in ontology): {skipped_props[:3]}...")
                
                if not property_mappings:
                    logger.warning(f"No valid property mappings for '{entity_name}', skipping eventhouse binding")
                    continue
                
                # Get timestamp column from eventhouse table config
                timestamp_col = "Timestamp"  # Default
                for table_config in yaml_config.eventhouse_tables:
                    if table_config.entity_name == entity_name:
                        timestamp_col = table_config.timestamp_column
                        break
                
                # For TimeSeries bindings, we should NOT reuse the existing binding ID
                # if that ID belongs to a NonTimeSeries binding. Each binding type needs
                # its own unique ID. Check if we've already added a Lakehouse binding.
                eventhouse_binding_id = None  # Will generate a new ID
                
                # Check if entity already has a Lakehouse binding in this session
                existing_bindings = builder.get_bindings().get(entity_id, [])
                has_lakehouse_binding = any(
                    b.binding_type.value == "NonTimeSeries" for b in existing_bindings
                )
                
                if not has_lakehouse_binding and existing_entity_binding_ids.get(entity_id):
                    # Entity has no Lakehouse binding in this session but has existing binding
                    # This means it's an eventhouse-only entity, can reuse existing ID
                    eventhouse_binding_id = existing_entity_binding_ids.get(entity_id)
                    logger.info(f"Reusing existing binding ID for eventhouse-only entity {entity_name}: {eventhouse_binding_id}")
                else:
                    logger.debug(f"Generating new binding ID for {entity_name} TimeSeries binding (entity has Lakehouse binding)")
                
                builder.add_eventhouse_binding(
                    entity_type_id=entity_id,
                    eventhouse_id=self.state.eventhouse_id,
                    database_name=database_name,
                    table_name=entity_binding.table_name,
                    key_column=entity_binding.key_column,
                    timestamp_column=timestamp_col,
                    property_mappings=property_mappings,
                    binding_id=eventhouse_binding_id,  # New ID for entities with both binding types
                )
                eventhouse_binding_count += 1
                logger.info(f"Added eventhouse binding: {entity_name} -> {entity_binding.table_name}")

        self._report_progress("configure_bindings", "in_progress", 70)

        # --- Add Relationship Contextualizations ---
        if self.state.lakehouse_id and yaml_config.lakehouse_relationships:
            for rel_binding in yaml_config.lakehouse_relationships:
                rel_name = rel_binding.relationship_name
                rel_id = relationship_name_to_id.get(rel_name)
                
                if not rel_id:
                    logger.warning(f"No relationship ID found for '{rel_name}', skipping contextualization")
                    continue
                
                # Get source and target entity key property IDs
                source_entity_name = rel_binding.source_entity
                target_entity_name = rel_binding.target_entity
                
                source_entity_id = entity_name_to_id.get(source_entity_name, "")
                target_entity_id = entity_name_to_id.get(target_entity_name, "")
                
                source_props = entity_id_to_properties.get(source_entity_id, {})
                target_props = entity_id_to_properties.get(target_entity_id, {})
                
                source_key_prop_id = source_props.get(rel_binding.source_key_column, rel_binding.source_key_column)
                target_key_prop_id = target_props.get(rel_binding.target_key_column, rel_binding.target_key_column)
                
                # Reuse existing contextualization ID if available
                existing_ctx_id = existing_rel_contextualization_ids.get(rel_id)
                
                builder.add_relationship_contextualization(
                    relationship_type_id=rel_id,
                    lakehouse_id=self.state.lakehouse_id,
                    table_name=rel_binding.table_name,
                    source_key_column=rel_binding.source_key_column,
                    source_key_property_id=source_key_prop_id,
                    target_key_column=rel_binding.target_key_column,
                    target_key_property_id=target_key_prop_id,
                    contextualization_id=existing_ctx_id,  # Reuse existing ID
                )
                relationship_binding_count += 1
                logger.info(f"Added relationship contextualization: {rel_name} -> {rel_binding.table_name}")

        self._report_progress("configure_bindings", "in_progress", 80)

        # Build and upload the binding definition
        total_bindings = lakehouse_binding_count + eventhouse_binding_count + relationship_binding_count
        
        if total_bindings == 0:
            return StepResult(
                status=StepStatus.SKIPPED,
                message="No valid bindings could be configured (entity IDs not found in ontology)",
                duration_seconds=time.time() - start,
            )

        try:
            # Build the definition parts with bindings
            binding_parts = builder.build_definition_parts(ont_definition)
            
            logger.info(f"Built {len(binding_parts)} parts for update")
            
            # Check for duplicate STATIC bindings per entity
            # Per Microsoft docs: Each entity supports ONE static binding, but MULTIPLE timeseries bindings
            entity_static_counts = {}
            entity_timeseries_counts = {}
            
            for part in binding_parts:
                path = part.get('path', 'unknown')
                logger.info(f"Part path: {path}")
                # Track bindings per entity for debugging
                if 'DataBindings' in path:
                    # Extract entity ID from path like EntityTypes/1000000001/DataBindings/uuid.json
                    parts = path.split('/')
                    if len(parts) >= 2:
                        entity_id = parts[1]
                        # Decode to check binding type
                        try:
                            import base64
                            decoded = base64.b64decode(part.get('payload', '')).decode('utf-8')
                            import json
                            binding_data = json.loads(decoded)
                            binding_type = binding_data.get('dataBindingConfiguration', {}).get('dataBindingType', '')
                            if binding_type == 'NonTimeSeries':
                                entity_static_counts[entity_id] = entity_static_counts.get(entity_id, 0) + 1
                            elif binding_type == 'TimeSeries':
                                entity_timeseries_counts[entity_id] = entity_timeseries_counts.get(entity_id, 0) + 1
                        except Exception:
                            # If we can't decode, count conservatively as static
                            entity_static_counts[entity_id] = entity_static_counts.get(entity_id, 0) + 1
                # Decode and log binding content for debugging
                if 'DataBindings' in path or 'Contextualizations' in path:
                    try:
                        import base64
                        decoded = base64.b64decode(part.get('payload', '')).decode('utf-8')
                        logger.debug(f"Part content: {decoded[:500]}...")
                    except Exception:
                        pass
            
            # Log entities with multiple STATIC bindings (this is the real constraint)
            for entity_id, count in entity_static_counts.items():
                ts_count = entity_timeseries_counts.get(entity_id, 0)
                if count > 1:
                    logger.error(f"Entity {entity_id} has {count} STATIC bindings - only 1 static allowed!")
                else:
                    logger.debug(f"Entity {entity_id}: {count} static binding(s), {ts_count} timeseries binding(s)")
            
            # Upload to Fabric
            self.fabric_client.update_ontology_definition(
                ontology_id=self.state.ontology_id,
                definition={"parts": binding_parts},
            )
            logger.info(f"Successfully uploaded {total_bindings} bindings to ontology")
        except Exception as e:
            logger.error(f"Failed to upload bindings: {e}")
            return StepResult(
                status=StepStatus.FAILED,
                message=f"Failed to upload bindings: {e}",
                error=e,
                duration_seconds=time.time() - start,
            )

        self._report_progress("configure_bindings", "in_progress", 90)

        # Validate bindings were created
        validation_errors = []
        try:
            updated_def = self.fabric_client.get_ontology_definition(self.state.ontology_id)
            updated_parts = updated_def.get("definition", {}).get("parts", [])
            if not updated_parts:
                updated_parts = updated_def.get("parts", [])
            
            # Count binding parts in the updated definition
            binding_part_count = sum(1 for p in updated_parts if "DataBindings" in p.get("path", ""))
            ctx_part_count = sum(1 for p in updated_parts if "Contextualizations" in p.get("path", ""))
            
            if binding_part_count < (lakehouse_binding_count + eventhouse_binding_count):
                validation_errors.append(
                    f"Expected {lakehouse_binding_count + eventhouse_binding_count} entity bindings, found {binding_part_count}"
                )
            if ctx_part_count < relationship_binding_count:
                validation_errors.append(
                    f"Expected {relationship_binding_count} relationship contextualizations, found {ctx_part_count}"
                )
            
            logger.info(f"Validation: Found {binding_part_count} entity bindings, {ctx_part_count} contextualizations")
        except Exception as e:
            logger.warning(f"Could not validate bindings: {e}")
            validation_errors.append(f"Validation failed: {e}")

        self.state.bindings_configured = True
        self._report_progress("configure_bindings", "completed", 100)

        message = (
            f"Configured {lakehouse_binding_count} lakehouse bindings, "
            f"{eventhouse_binding_count} eventhouse bindings, "
            f"{relationship_binding_count} relationship contextualizations"
        )
        
        if validation_errors:
            message += f" (validation warnings: {'; '.join(validation_errors)})"

        return StepResult(
            status=StepStatus.COMPLETED,
            message=message,
            duration_seconds=time.time() - start,
            details={
                "lakehouse_bindings": lakehouse_binding_count,
                "eventhouse_bindings": eventhouse_binding_count,
                "relationship_contextualizations": relationship_binding_count,
                "validation_errors": validation_errors,
            }
        )

    def _convert_markdown_to_yaml_config(self, parsed_bindings: Dict[str, List]) -> YamlBindingsConfig:
        """Convert markdown-parsed bindings to YamlBindingsConfig format for unified processing."""
        config = YamlBindingsConfig()
        config.lakehouse_entities = parsed_bindings.get("static", [])
        config.lakehouse_relationships = parsed_bindings.get("relationships", [])
        config.eventhouse_entities = parsed_bindings.get("timeseries", [])
        return config

    def _step_bind_static(self) -> StepResult:
        """
        Bind lakehouse (static/NonTimeSeries) properties for all entities.
        
        This is step 8 from ResearchFixes.md:
        - Binds lakehouse properties for all entities as per bindings.yaml
        - Ensures the key column (keyColumn) is defined
        - Validates all bindings are successful
        """
        import base64
        import json
        
        start = time.time()
        self._check_cancellation()
        self._report_progress("bind_static", "in_progress", 0)
        
        if not self.state.ontology_id:
            return StepResult(
                status=StepStatus.FAILED,
                message="Ontology not created. Run create_ontology step first.",
                duration_seconds=time.time() - start,
            )
        
        if not self.state.lakehouse_id:
            return StepResult(
                status=StepStatus.SKIPPED,
                message="No lakehouse configured, skipping static bindings",
                duration_seconds=time.time() - start,
            )
        
        # Parse bindings configuration
        yaml_config = parse_bindings_yaml(self.config.demo_path)
        if not yaml_config or not yaml_config.lakehouse_entities:
            return StepResult(
                status=StepStatus.SKIPPED,
                message="No lakehouse entity bindings found in bindings.yaml",
                duration_seconds=time.time() - start,
            )
        
        # Get ontology definition to extract entity IDs and property IDs
        try:
            ont_definition = self.fabric_client.get_ontology_definition(self.state.ontology_id)
        except Exception as e:
            return StepResult(
                status=StepStatus.FAILED,
                message=f"Failed to get ontology definition: {e}",
                error=e,
                duration_seconds=time.time() - start,
            )
        
        entity_name_to_id, entity_id_to_properties, _, existing_entity_binding_ids, _ = \
            self._parse_ontology_mappings(ont_definition)
        
        self._report_progress("bind_static", "in_progress", 30)
        
        # Build bindings
        builder = OntologyBindingBuilder(
            workspace_id=self.config.fabric.workspace_id,
            ontology_id=self.state.ontology_id,
        )
        
        binding_count = 0
        skipped = []
        
        for entity_binding in yaml_config.lakehouse_entities:
            entity_name = entity_binding.entity_name
            entity_id = entity_name_to_id.get(entity_name)
            
            if not entity_id:
                logger.warning(f"No entity ID found for '{entity_name}', skipping binding")
                skipped.append(entity_name)
                continue
            
            # Validate key column is defined
            if not entity_binding.key_column:
                logger.warning(f"No key column defined for '{entity_name}', skipping")
                skipped.append(entity_name)
                continue
            
            # Get property mappings
            entity_props = entity_id_to_properties.get(entity_id, {})
            property_mappings = {}
            
            for pm in entity_binding.property_mappings:
                prop_id = entity_props.get(pm.target_property)
                if prop_id:
                    property_mappings[pm.source_column] = prop_id
            
            if not property_mappings:
                logger.warning(f"No valid property mappings for '{entity_name}', skipping")
                skipped.append(entity_name)
                continue
            
            existing_binding_id = existing_entity_binding_ids.get(entity_id)
            
            builder.add_lakehouse_binding(
                entity_type_id=entity_id,
                lakehouse_id=self.state.lakehouse_id,
                table_name=entity_binding.table_name,
                key_column=entity_binding.key_column,
                property_mappings=property_mappings,
                binding_id=existing_binding_id,
            )
            
            builder.register_entity_key_property(
                entity_name,
                entity_props.get(entity_binding.key_column, entity_binding.key_column)
            )
            
            binding_count += 1
            logger.info(f"Added static binding: {entity_name} -> {entity_binding.table_name} (key: {entity_binding.key_column})")
        
        self._report_progress("bind_static", "in_progress", 70)
        
        if binding_count == 0:
            return StepResult(
                status=StepStatus.SKIPPED,
                message=f"No valid static bindings configured (skipped: {', '.join(skipped)})",
                duration_seconds=time.time() - start,
            )
        
        # Upload bindings
        try:
            binding_parts = builder.build_definition_parts(ont_definition)
            self.fabric_client.update_ontology_definition(
                ontology_id=self.state.ontology_id,
                definition={"parts": binding_parts},
            )
            logger.info(f"Uploaded {binding_count} static bindings")
        except Exception as e:
            return StepResult(
                status=StepStatus.FAILED,
                message=f"Failed to upload static bindings: {e}",
                error=e,
                duration_seconds=time.time() - start,
            )
        
        self._report_progress("bind_static", "completed", 100)
        
        return StepResult(
            status=StepStatus.COMPLETED,
            message=f"Configured {binding_count} static (lakehouse) bindings",
            duration_seconds=time.time() - start,
            details={
                "binding_count": binding_count,
                "skipped": skipped,
            }
        )

    def _step_bind_timeseries(self) -> StepResult:
        """
        Bind eventhouse (timeseries) properties for all entities.
        
        This is step 9 from ResearchFixes.md:
        - Binds eventhouse properties for all entities as per bindings.yaml
        - Validates all timeseries bindings are successful
        """
        import base64
        import json
        
        start = time.time()
        self._check_cancellation()
        self._report_progress("bind_timeseries", "in_progress", 0)
        
        if not self.state.ontology_id:
            return StepResult(
                status=StepStatus.FAILED,
                message="Ontology not created. Run create_ontology step first.",
                duration_seconds=time.time() - start,
            )
        
        if not self.state.eventhouse_id:
            return StepResult(
                status=StepStatus.SKIPPED,
                message="No eventhouse configured, skipping timeseries bindings",
                duration_seconds=time.time() - start,
            )
        
        # Parse bindings configuration
        yaml_config = parse_bindings_yaml(self.config.demo_path)
        if not yaml_config or not yaml_config.eventhouse_entities:
            return StepResult(
                status=StepStatus.SKIPPED,
                message="No eventhouse entity bindings found in bindings.yaml",
                duration_seconds=time.time() - start,
            )
        
        # Get ontology definition
        try:
            ont_definition = self.fabric_client.get_ontology_definition(self.state.ontology_id)
        except Exception as e:
            return StepResult(
                status=StepStatus.FAILED,
                message=f"Failed to get ontology definition: {e}",
                error=e,
                duration_seconds=time.time() - start,
            )
        
        entity_name_to_id, entity_id_to_properties, _, existing_entity_binding_ids, _ = \
            self._parse_ontology_mappings(ont_definition)
        
        self._report_progress("bind_timeseries", "in_progress", 30)
        
        # Get KQL database name
        try:
            kql_db = self.fabric_client.get_kql_database(self.state.kql_database_id)
            database_name = kql_db.get("displayName", self.config.resources.eventhouse.name)
        except Exception:
            database_name = self.config.resources.eventhouse.name
        
        # Build bindings
        builder = OntologyBindingBuilder(
            workspace_id=self.config.fabric.workspace_id,
            ontology_id=self.state.ontology_id,
        )
        
        binding_count = 0
        skipped = []
        
        for entity_binding in yaml_config.eventhouse_entities:
            entity_name = entity_binding.entity_name
            entity_id = entity_name_to_id.get(entity_name)
            
            if not entity_id:
                logger.warning(f"No entity ID found for '{entity_name}', skipping")
                skipped.append(entity_name)
                continue
            
            entity_props = entity_id_to_properties.get(entity_id, {})
            property_mappings = {}
            
            for pm in entity_binding.property_mappings:
                prop_id = entity_props.get(pm.target_property)
                if prop_id:
                    property_mappings[pm.source_column] = prop_id
            
            if not property_mappings:
                logger.warning(f"No valid property mappings for '{entity_name}', skipping")
                skipped.append(entity_name)
                continue
            
            # Get timestamp column
            timestamp_col = "Timestamp"
            for table_config in yaml_config.eventhouse_tables:
                if table_config.entity_name == entity_name:
                    timestamp_col = table_config.timestamp_column
                    break
            
            existing_binding_id = existing_entity_binding_ids.get(entity_id)
            
            builder.add_eventhouse_binding(
                entity_type_id=entity_id,
                eventhouse_id=self.state.eventhouse_id,
                database_name=database_name,
                table_name=entity_binding.table_name,
                key_column=entity_binding.key_column,
                timestamp_column=timestamp_col,
                property_mappings=property_mappings,
                binding_id=existing_binding_id,
            )
            
            binding_count += 1
            logger.info(f"Added timeseries binding: {entity_name} -> {entity_binding.table_name}")
        
        self._report_progress("bind_timeseries", "in_progress", 70)
        
        if binding_count == 0:
            return StepResult(
                status=StepStatus.SKIPPED,
                message=f"No valid timeseries bindings configured (skipped: {', '.join(skipped)})",
                duration_seconds=time.time() - start,
            )
        
        # Upload bindings
        try:
            binding_parts = builder.build_definition_parts(ont_definition)
            self.fabric_client.update_ontology_definition(
                ontology_id=self.state.ontology_id,
                definition={"parts": binding_parts},
            )
            logger.info(f"Uploaded {binding_count} timeseries bindings")
        except Exception as e:
            return StepResult(
                status=StepStatus.FAILED,
                message=f"Failed to upload timeseries bindings: {e}",
                error=e,
                duration_seconds=time.time() - start,
            )
        
        self._report_progress("bind_timeseries", "completed", 100)
        
        return StepResult(
            status=StepStatus.COMPLETED,
            message=f"Configured {binding_count} timeseries (eventhouse) bindings",
            duration_seconds=time.time() - start,
            details={
                "binding_count": binding_count,
                "skipped": skipped,
            }
        )

    def _step_bind_relationships(self) -> StepResult:
        """
        Bind all relationship contextualizations.
        
        This is step 10 from ResearchFixes.md:
        - Binds all relationships as per bindings.yaml
        - Validates all relationship bindings are successful
        """
        import base64
        import json
        
        start = time.time()
        self._check_cancellation()
        self._report_progress("bind_relationships", "in_progress", 0)
        
        if not self.state.ontology_id:
            return StepResult(
                status=StepStatus.FAILED,
                message="Ontology not created. Run create_ontology step first.",
                duration_seconds=time.time() - start,
            )
        
        if not self.state.lakehouse_id:
            return StepResult(
                status=StepStatus.SKIPPED,
                message="No lakehouse configured, skipping relationship bindings",
                duration_seconds=time.time() - start,
            )
        
        # Parse bindings configuration
        yaml_config = parse_bindings_yaml(self.config.demo_path)
        if not yaml_config or not yaml_config.lakehouse_relationships:
            return StepResult(
                status=StepStatus.SKIPPED,
                message="No relationship bindings found in bindings.yaml",
                duration_seconds=time.time() - start,
            )
        
        # Get ontology definition
        try:
            ont_definition = self.fabric_client.get_ontology_definition(self.state.ontology_id)
        except Exception as e:
            return StepResult(
                status=StepStatus.FAILED,
                message=f"Failed to get ontology definition: {e}",
                error=e,
                duration_seconds=time.time() - start,
            )
        
        entity_name_to_id, entity_id_to_properties, relationship_name_to_id, _, existing_rel_ctx_ids = \
            self._parse_ontology_mappings(ont_definition)
        
        self._report_progress("bind_relationships", "in_progress", 30)
        
        # Build contextualizations
        builder = OntologyBindingBuilder(
            workspace_id=self.config.fabric.workspace_id,
            ontology_id=self.state.ontology_id,
        )
        
        binding_count = 0
        skipped = []
        
        for rel_binding in yaml_config.lakehouse_relationships:
            rel_name = rel_binding.relationship_name
            rel_id = relationship_name_to_id.get(rel_name)
            
            if not rel_id:
                logger.warning(f"No relationship ID found for '{rel_name}', skipping")
                skipped.append(rel_name)
                continue
            
            # Get source and target entity key property IDs
            source_entity_id = entity_name_to_id.get(rel_binding.source_entity, "")
            target_entity_id = entity_name_to_id.get(rel_binding.target_entity, "")
            
            source_props = entity_id_to_properties.get(source_entity_id, {})
            target_props = entity_id_to_properties.get(target_entity_id, {})
            
            source_key_prop_id = source_props.get(rel_binding.source_key_column, rel_binding.source_key_column)
            target_key_prop_id = target_props.get(rel_binding.target_key_column, rel_binding.target_key_column)
            
            existing_ctx_id = existing_rel_ctx_ids.get(rel_id)
            
            builder.add_relationship_contextualization(
                relationship_type_id=rel_id,
                lakehouse_id=self.state.lakehouse_id,
                table_name=rel_binding.table_name,
                source_key_column=rel_binding.source_key_column,
                source_key_property_id=source_key_prop_id,
                target_key_column=rel_binding.target_key_column,
                target_key_property_id=target_key_prop_id,
                contextualization_id=existing_ctx_id,
            )
            
            binding_count += 1
            logger.info(f"Added relationship contextualization: {rel_name} -> {rel_binding.table_name}")
        
        self._report_progress("bind_relationships", "in_progress", 70)
        
        if binding_count == 0:
            return StepResult(
                status=StepStatus.SKIPPED,
                message=f"No valid relationship bindings configured (skipped: {', '.join(skipped)})",
                duration_seconds=time.time() - start,
            )
        
        # Upload bindings
        try:
            binding_parts = builder.build_definition_parts(ont_definition)
            self.fabric_client.update_ontology_definition(
                ontology_id=self.state.ontology_id,
                definition={"parts": binding_parts},
            )
            logger.info(f"Uploaded {binding_count} relationship contextualizations")
        except Exception as e:
            return StepResult(
                status=StepStatus.FAILED,
                message=f"Failed to upload relationship bindings: {e}",
                error=e,
                duration_seconds=time.time() - start,
            )
        
        self._report_progress("bind_relationships", "completed", 100)
        
        return StepResult(
            status=StepStatus.COMPLETED,
            message=f"Configured {binding_count} relationship contextualizations",
            duration_seconds=time.time() - start,
            details={
                "binding_count": binding_count,
                "skipped": skipped,
            }
        )

    def _parse_ontology_mappings(self, ont_definition: Dict) -> tuple:
        """
        Parse ontology definition to extract entity, relationship, and property mappings.
        
        Returns:
            Tuple of (entity_name_to_id, entity_id_to_properties, relationship_name_to_id, 
                     existing_entity_binding_ids, existing_rel_ctx_ids)
        """
        import base64
        import json
        
        entity_name_to_id = {}
        entity_id_to_properties = {}
        relationship_name_to_id = {}
        existing_entity_binding_ids = {}
        existing_rel_ctx_ids = {}
        
        parts = ont_definition.get("definition", {}).get("parts", [])
        if not parts:
            parts = ont_definition.get("parts", [])
        
        for part in parts:
            path = part.get("path", "")
            payload_b64 = part.get("payload", "")
            
            if not payload_b64:
                continue
            
            try:
                payload_json = base64.b64decode(payload_b64).decode("utf-8")
                payload = json.loads(payload_json)
            except Exception:
                continue
            
            # Extract entity type mappings
            if "EntityTypes/" in path and "DataBindings" not in path:
                entity_id = payload.get("id", "")
                entity_name = payload.get("name", "")
                if entity_id and entity_name:
                    entity_name_to_id[entity_name] = entity_id
                    props = {}
                    for prop in payload.get("properties", []):
                        prop_name = prop.get("name", "")
                        prop_id = prop.get("id", "")
                        if prop_name and prop_id:
                            props[prop_name] = prop_id
                    entity_id_to_properties[entity_id] = props
            
            # Extract relationship type mappings
            elif "RelationshipTypes/" in path and "Contextualizations" not in path:
                rel_id = payload.get("id", "")
                rel_name = payload.get("name", "")
                if rel_id and rel_name:
                    relationship_name_to_id[rel_name] = rel_id
            
            # Extract existing binding IDs
            elif "/DataBindings/" in path:
                parts_split = path.split("/")
                if len(parts_split) >= 4:
                    entity_id = parts_split[1]
                    binding_file = parts_split[3]
                    binding_id = binding_file.replace(".json", "")
                    existing_entity_binding_ids[entity_id] = binding_id
            
            # Extract existing contextualization IDs
            elif "/Contextualizations/" in path:
                parts_split = path.split("/")
                if len(parts_split) >= 4:
                    rel_id = parts_split[1]
                    ctx_file = parts_split[3]
                    ctx_id = ctx_file.replace(".json", "")
                    existing_rel_ctx_ids[rel_id] = ctx_id
        
        return (entity_name_to_id, entity_id_to_properties, relationship_name_to_id,
                existing_entity_binding_ids, existing_rel_ctx_ids)

    # =========================================================================
    # SDK Bridge Helpers (Phase 3)
    # =========================================================================

    def _create_sdk_binding_bridge(
        self,
        cluster_uri: Optional[str] = None,
    ) -> SDKBindingBridge:
        """
        Create an SDK binding bridge configured for this demo.
        
        This method creates a new SDKBindingBridge with the current workspace,
        lakehouse, and eventhouse configuration.
        
        Args:
            cluster_uri: Optional eventhouse cluster URI
            
        Returns:
            Configured SDKBindingBridge instance
        """
        return SDKBindingBridge(
            workspace_id=self.config.fabric.workspace_id,
            lakehouse_id=self.state.lakehouse_id,
            eventhouse_id=self.state.eventhouse_id,
            database_name=self.state.kql_database_name,
            cluster_uri=cluster_uri,
        )

    def _build_entity_binding_config(
        self,
        entity_binding,
        binding_type: str = "static",
        timestamp_column: Optional[str] = None,
        database_name: Optional[str] = None,
        cluster_uri: Optional[str] = None,
    ) -> EntityBindingConfig:
        """
        Build an EntityBindingConfig from a parsed YAML entity binding.
        
        Args:
            entity_binding: Parsed entity binding from YAML config
            binding_type: "static" or "timeseries"
            timestamp_column: Timestamp column for timeseries bindings
            database_name: Database name for eventhouse bindings
            cluster_uri: Cluster URI for eventhouse bindings
            
        Returns:
            EntityBindingConfig ready for SDKBindingBridge
        """
        column_mappings = {
            pm.target_property: pm.source_column
            for pm in entity_binding.property_mappings
        }
        
        return EntityBindingConfig(
            entity_name=entity_binding.entity_name,
            binding_type=binding_type,
            table_name=entity_binding.table_name,
            key_column=entity_binding.key_column,
            column_mappings=column_mappings,
            timestamp_column=timestamp_column,
            database_name=database_name,
            cluster_uri=cluster_uri,
        )

    def _build_relationship_context_config(
        self,
        rel_binding,
        source_type: str = "lakehouse",
        database_name: Optional[str] = None,
    ) -> RelationshipContextConfig:
        """
        Build a RelationshipContextConfig from a parsed YAML relationship binding.
        
        Args:
            rel_binding: Parsed relationship binding from YAML config
            source_type: "lakehouse" or "eventhouse"
            database_name: Database name for eventhouse contextualizations
            
        Returns:
            RelationshipContextConfig ready for SDKBindingBridge
        """
        return RelationshipContextConfig(
            relationship_name=rel_binding.relationship_name,
            source_entity=rel_binding.source_entity,
            target_entity=rel_binding.target_entity,
            source_type=source_type,
            table_name=rel_binding.table_name,
            source_key_column=rel_binding.source_key_column,
            target_key_column=rel_binding.target_key_column,
            database_name=database_name,
        )

    def _get_eventhouse_cluster_uri(self) -> Optional[str]:
        """
        Get the Eventhouse cluster URI for the current eventhouse.
        
        Returns:
            Cluster URI string or None if not available
        """
        if not self.state.eventhouse_id:
            return None
        
        try:
            eventhouse_info = self.fabric_client.get_eventhouse(self.state.eventhouse_id)
            # Extract cluster URI from eventhouse properties
            properties = eventhouse_info.get("properties", {})
            query_uri = properties.get("queryServiceUri")
            if query_uri:
                return query_uri
            
            # Fallback: construct from eventhouse name
            workspace_name = self.config.fabric.workspace_id
            return f"https://{self.state.eventhouse_name}.kusto.fabric.microsoft.com"
        except Exception as e:
            logger.warning(f"Could not get eventhouse cluster URI: {e}")
            return None

    def _step_verify_setup(self) -> StepResult:
        """
        Comprehensive verification of the entire setup.
        
        Checks:
        1. Lakehouse exists with all expected tables
        2. Eventhouse exists with all expected KQL tables and data
        3. Ontology exists with all entities and properties
        4. Static data bindings are configured
        5. Timeseries data bindings are configured
        """
        start = time.time()
        self._report_progress("verify", "in_progress", 0)

        checks_passed = []
        checks_failed = []
        checks_warnings = []
        verification_details = {}

        # --- 1. Verify Lakehouse ---
        if self.state.lakehouse_id:
            try:
                lh = self.fabric_client.get_lakehouse(self.state.lakehouse_id)
                if lh:
                    checks_passed.append(f"✓ Lakehouse exists: {self.state.lakehouse_name}")
                    
                    # Check all expected tables exist
                    expected_tables = {f.stem for f in self.config.get_lakehouse_csv_files()}
                    existing_tables = self._get_existing_lakehouse_tables()
                    
                    missing_tables = expected_tables - existing_tables
                    if missing_tables:
                        checks_failed.append(f"✗ Lakehouse missing tables: {', '.join(missing_tables)}")
                    else:
                        checks_passed.append(f"✓ Lakehouse has all {len(expected_tables)} expected tables")
                    
                    verification_details["lakehouse"] = {
                        "id": self.state.lakehouse_id,
                        "name": self.state.lakehouse_name,
                        "expected_tables": list(expected_tables),
                        "existing_tables": list(existing_tables),
                        "missing_tables": list(missing_tables),
                    }
                else:
                    checks_failed.append(f"✗ Lakehouse not found: {self.state.lakehouse_id}")
            except Exception as e:
                checks_failed.append(f"✗ Lakehouse verification failed: {e}")
        elif self.config.resources.lakehouse.enabled:
            checks_failed.append("✗ Lakehouse was enabled but not created")

        self._report_progress("verify", "in_progress", 25)

        # --- 2. Verify Eventhouse ---
        if self.state.eventhouse_id:
            try:
                eh = self.fabric_client.get_eventhouse(self.state.eventhouse_id)
                if eh:
                    checks_passed.append(f"✓ Eventhouse exists: {self.state.eventhouse_name}")
                    
                    # Check KQL database exists
                    if self.state.kql_database_id:
                        checks_passed.append(f"✓ KQL Database exists: {self.state.kql_database_name}")
                        
                        # Check all expected KQL tables exist with data
                        expected_eh_tables = {f.stem for f in self.config.get_eventhouse_csv_files()}
                        existing_eh_tables = self._get_existing_eventhouse_tables()
                        
                        missing_eh_tables = expected_eh_tables - existing_eh_tables
                        if missing_eh_tables:
                            checks_failed.append(f"✗ Eventhouse missing tables: {', '.join(missing_eh_tables)}")
                        else:
                            checks_passed.append(f"✓ Eventhouse has all {len(expected_eh_tables)} expected tables")
                        
                        # Check tables have data
                        tables_with_data = {}
                        empty_tables = []
                        for table_name in existing_eh_tables & expected_eh_tables:
                            try:
                                count = self.eventhouse_client.get_table_count(
                                    eventhouse_id=self.state.eventhouse_id,
                                    database_name=self.state.kql_database_name,
                                    table_name=table_name,
                                )
                                tables_with_data[table_name] = count
                                if count == 0:
                                    empty_tables.append(table_name)
                            except Exception:
                                pass
                        
                        if empty_tables:
                            checks_warnings.append(f"⚠ Eventhouse tables with no data: {', '.join(empty_tables)}")
                        else:
                            checks_passed.append(f"✓ All eventhouse tables have data")
                        
                        verification_details["eventhouse"] = {
                            "id": self.state.eventhouse_id,
                            "name": self.state.eventhouse_name,
                            "kql_database_id": self.state.kql_database_id,
                            "kql_database_name": self.state.kql_database_name,
                            "expected_tables": list(expected_eh_tables),
                            "existing_tables": list(existing_eh_tables),
                            "missing_tables": list(missing_eh_tables),
                            "table_row_counts": tables_with_data,
                        }
                    else:
                        checks_failed.append("✗ KQL Database not found for Eventhouse")
                else:
                    checks_failed.append(f"✗ Eventhouse not found: {self.state.eventhouse_id}")
            except Exception as e:
                checks_failed.append(f"✗ Eventhouse verification failed: {e}")
        elif self.config.resources.eventhouse.enabled:
            checks_failed.append("✗ Eventhouse was enabled but not created")

        self._report_progress("verify", "in_progress", 50)

        # --- 3. Verify Ontology ---
        if self.state.ontology_id:
            try:
                ont = self.fabric_client.get_ontology(self.state.ontology_id)
                if ont:
                    checks_passed.append(f"✓ Ontology exists: {self.state.ontology_name}")
                    
                    # Get ontology definition to verify entities and relationships
                    try:
                        ont_def = self.fabric_client.get_ontology_definition(self.state.ontology_id)
                        
                        # Count entities and relationships from definition parts
                        entity_count = 0
                        relationship_count = 0
                        property_count = 0
                        
                        for part in ont_def.get("definition", {}).get("parts", []):
                            path = part.get("path", "")
                            if "EntityTypes" in path and path.endswith(".json"):
                                entity_count += 1
                            elif "RelationshipTypes" in path and path.endswith(".json"):
                                relationship_count += 1
                            elif "Properties" in path and path.endswith(".json"):
                                property_count += 1
                        
                        checks_passed.append(f"✓ Ontology has {entity_count} entities, {relationship_count} relationships, {property_count} properties")
                        
                        verification_details["ontology"] = {
                            "id": self.state.ontology_id,
                            "name": self.state.ontology_name,
                            "entity_count": entity_count,
                            "relationship_count": relationship_count,
                            "property_count": property_count,
                        }
                    except Exception as e:
                        checks_warnings.append(f"⚠ Could not retrieve ontology definition: {e}")
                else:
                    checks_failed.append(f"✗ Ontology not found: {self.state.ontology_id}")
            except Exception as e:
                checks_failed.append(f"✗ Ontology verification failed: {e}")
        elif self.config.resources.ontology.enabled:
            checks_failed.append("✗ Ontology was enabled but not created")

        self._report_progress("verify", "in_progress", 75)

        # --- 4. Verify Bindings ---
        if self.state.bindings_configured:
            checks_passed.append("✓ Data bindings configured")
        elif self.state.ontology_id:
            checks_warnings.append("⚠ Bindings not configured (ontology exists but bindings may need manual setup)")

        # --- Summary ---
        self._report_progress("verify", "completed", 100)
        
        total_checks = len(checks_passed) + len(checks_failed) + len(checks_warnings)
        
        all_details = {
            "passed": checks_passed,
            "failed": checks_failed,
            "warnings": checks_warnings,
            "verification": verification_details,
        }

        if checks_failed:
            return StepResult(
                status=StepStatus.FAILED,
                message=f"Verification: {len(checks_passed)} passed, {len(checks_failed)} failed, {len(checks_warnings)} warnings",
                duration_seconds=time.time() - start,
                details=all_details,
            )

        if checks_warnings:
            return StepResult(
                status=StepStatus.COMPLETED,
                message=f"Verification: {len(checks_passed)} passed, {len(checks_warnings)} warnings",
                duration_seconds=time.time() - start,
                details=all_details,
            )

        return StepResult(
            status=StepStatus.COMPLETED,
            message=f"All {len(checks_passed)} verification checks passed",
            duration_seconds=time.time() - start,
            details=all_details,
        )

    def _step_refresh_graph(self) -> StepResult:
        """
        Refresh the graph item associated with the ontology.
        
        This step triggers an on-demand refresh job for the graph item
        to ensure all bound data is synced after bindings are configured.
        
        The graph item is automatically created by Fabric when an ontology
        has data bindings configured, and is named:
        {OntologyName}_graph_{ontologyIdWithoutDashes}
        """
        start = time.time()
        self._report_progress("refresh_graph", "in_progress", 0)
        
        if not self.state.ontology_id:
            return StepResult(
                status=StepStatus.SKIPPED,
                message="No ontology ID available - skipping graph refresh",
                duration_seconds=time.time() - start,
            )
        
        if not self.state.ontology_name:
            return StepResult(
                status=StepStatus.SKIPPED,
                message="No ontology name available - skipping graph refresh",
                duration_seconds=time.time() - start,
            )
        
        try:
            self._report_progress("refresh_graph", "in_progress", 10)
            
            # Find the graph item associated with the ontology
            graph_item = self.fabric_client.find_ontology_graph(
                ontology_name=self.state.ontology_name,
                ontology_id=self.state.ontology_id,
            )
            
            if not graph_item:
                # Graph might not be accessible via REST API yet or hasn't been created
                # The Graph in Microsoft Fabric item type is managed internally by Fabric
                ontology_id_clean = self.state.ontology_id.replace("-", "")
                expected_graph_name = f"{self.state.ontology_name}_graph_{ontology_id_clean}"
                
                return StepResult(
                    status=StepStatus.COMPLETED,
                    message=f"Graph refresh requires manual action. Please refresh the graph "
                            f"'{expected_graph_name}' from the Fabric portal: "
                            f"Workspace → Graph item → Schedule → Refresh now",
                    duration_seconds=time.time() - start,
                    details={
                        "ontology_id": self.state.ontology_id,
                        "ontology_name": self.state.ontology_name,
                        "expected_graph_name": expected_graph_name,
                        "action": "manual_refresh_required",
                        "instructions": [
                            "1. Open the Fabric workspace in your browser",
                            f"2. Locate the graph item: '{expected_graph_name}'",
                            "3. Click '...' to expand the options menu",
                            "4. Select 'Schedule'",
                            "5. Click 'Refresh now' to sync the data",
                        ],
                    },
                )
            
            graph_id = graph_item.get("id")
            graph_name = graph_item.get("displayName")
            logger.info(f"Found graph item: {graph_name} ({graph_id})")
            
            self._report_progress("refresh_graph", "in_progress", 30)
            
            # Trigger refresh job
            logger.info(f"Triggering refresh for graph: {graph_name}")
            
            def progress_callback(status: str, percent: float):
                self._report_progress("refresh_graph", "in_progress", 30 + (percent * 0.6))
            
            result = self.fabric_client.refresh_graph(
                graph_id=graph_id,
                timeout_seconds=600,
                progress_callback=progress_callback,
            )
            
            self._report_progress("refresh_graph", "completed", 100)
            
            return StepResult(
                status=StepStatus.COMPLETED,
                message=f"Graph '{graph_name}' refresh completed successfully",
                artifact_id=graph_id,
                artifact_name=graph_name,
                duration_seconds=time.time() - start,
                details={
                    "graph_id": graph_id,
                    "graph_name": graph_name,
                    "refresh_result": result,
                },
            )
            
        except Exception as e:
            logger.warning(f"Graph refresh failed (non-critical): {e}")
            # Graph refresh is not critical - the graph can be refreshed manually
            return StepResult(
                status=StepStatus.COMPLETED,
                message=f"Graph refresh skipped: {str(e)}. You can manually refresh the graph "
                        f"'{self.state.ontology_name}_graph_*' from the Fabric portal.",
                duration_seconds=time.time() - start,
                details={
                    "error": str(e),
                    "ontology_id": self.state.ontology_id,
                    "ontology_name": self.state.ontology_name,
                    "action": "manual_refresh_recommended",
                },
            )

    def _dry_run_summary(self) -> Dict[str, StepResult]:
        """Generate summary for dry run mode."""
        results = {}

        # List what would be created
        if self.config.resources.lakehouse.enabled:
            results["create_lakehouse"] = StepResult(
                status=StepStatus.PENDING,
                message=f"Would create Lakehouse: {self.config.resources.lakehouse.name}",
            )

        csv_files = self.config.get_lakehouse_csv_files()
        if csv_files:
            results["upload_files"] = StepResult(
                status=StepStatus.PENDING,
                message=f"Would upload {len(csv_files)} CSV files",
                details={"files": [f.name for f in csv_files]},
            )

        if self.config.resources.eventhouse.enabled:
            results["create_eventhouse"] = StepResult(
                status=StepStatus.PENDING,
                message=f"Would create Eventhouse: {self.config.resources.eventhouse.name}",
            )

        if self.config.resources.ontology.enabled:
            results["create_ontology"] = StepResult(
                status=StepStatus.PENDING,
                message=f"Would create Ontology: {self.config.resources.ontology.name}",
            )

            results["refresh_graph"] = StepResult(
                status=StepStatus.PENDING,
                message=f"Would refresh graph for Ontology: {self.config.resources.ontology.name}",
            )

        return results

    def _report_progress(self, step: str, status: str, percent: float) -> None:
        """Report progress to callback if provided."""
        if self.progress_callback:
            self.progress_callback(step, status, percent)

    def _cleanup_clients(self) -> None:
        """Clean up client resources."""
        if self._fabric_client:
            self._fabric_client.close()
        if self._onelake_client:
            self._onelake_client.close()

    def get_state(self) -> SetupState:
        """Get current setup state."""
        return self.state


def print_setup_results(results: Dict[str, StepResult]) -> None:
    """Print setup results in a formatted table."""
    table = Table(title="Demo Setup Results")
    table.add_column("Step", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Message")
    table.add_column("Duration")

    status_styles = {
        StepStatus.COMPLETED: "[green]✓ Completed[/green]",
        StepStatus.FAILED: "[red]✗ Failed[/red]",
        StepStatus.SKIPPED: "[yellow]○ Skipped[/yellow]",
        StepStatus.PENDING: "[blue]◌ Pending[/blue]",
        StepStatus.IN_PROGRESS: "[cyan]◐ In Progress[/cyan]",
    }

    for step_name, result in results.items():
        status_str = status_styles.get(result.status, str(result.status))
        duration = f"{result.duration_seconds:.1f}s" if result.duration_seconds else "-"
        table.add_row(step_name, status_str, result.message, duration)

    console.print(table)
