"""
Command-line interface for Fabric Demo Automation.

Provides commands for:
- init: Create demo.yaml template
- validate: Validate demo package structure
- setup: Run complete demo setup
- status: Check demo resource status
- cleanup: Remove demo resources
"""

import argparse
import sys
import logging
from pathlib import Path
from enum import Enum

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.logging import RichHandler

from .core.config import DemoConfiguration, generate_demo_yaml_template
from .core.errors import DemoAutomationError, ConfigurationError
from .orchestrator import DemoOrchestrator, print_setup_results


console = Console()


class OutputFormat(Enum):
    """Output format options."""
    TEXT = "text"
    JSON = "json"
    YAML = "yaml"


def setup_logging(verbose: bool = False) -> None:
    """Configure logging with rich handler."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )


def create_parser() -> argparse.ArgumentParser:
    """Create the main CLI parser."""
    parser = argparse.ArgumentParser(
        prog="fabric-demo",
        description="Fabric Ontology Demo Automation Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  fabric-demo init ./MedicalManufacturing
  fabric-demo validate ./MedicalManufacturing
  fabric-demo setup ./MedicalManufacturing --workspace-id abc123
  fabric-demo setup ./MedicalManufacturing --dry-run
  fabric-demo run-step ./MedicalManufacturing --step create_lakehouse
  fabric-demo run-step ./MedicalManufacturing --step 2
  fabric-demo status ./MedicalManufacturing
  fabric-demo cleanup ./MedicalManufacturing --confirm
        """,
    )

    # Global options
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # init command
    init_parser = subparsers.add_parser(
        "init",
        help="Create demo.yaml template in existing demo folder",
    )
    init_parser.add_argument(
        "demo_path",
        type=str,
        help="Path to the demo folder",
    )
    init_parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Overwrite existing demo.yaml",
    )

    # validate command
    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate demo package structure",
    )
    validate_parser.add_argument(
        "demo_path",
        type=str,
        help="Path to the demo folder",
    )
    validate_parser.add_argument(
        "--output-format", "-o",
        type=str,
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    validate_parser.add_argument(
        "--show-details", "-d",
        action="store_true",
        help="Show detailed validation results including all info messages",
    )

    # setup command
    setup_parser = subparsers.add_parser(
        "setup",
        help="Run complete demo setup",
    )
    setup_parser.add_argument(
        "demo_path",
        type=str,
        help="Path to the demo folder",
    )
    setup_parser.add_argument(
        "--workspace-id", "-w",
        type=str,
        help="Fabric workspace ID (overrides config/env)",
    )
    setup_parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Preview actions without executing",
    )
    setup_parser.add_argument(
        "--skip-existing",
        action="store_true",
        default=True,
        help="Skip creation of existing resources (default: true)",
    )
    setup_parser.add_argument(
        "--no-skip-existing",
        action="store_false",
        dest="skip_existing",
        help="Fail if resources already exist",
    )
    setup_parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Prompt Y/N when resources already exist",
    )
    setup_parser.add_argument(
        "--resume", "-r",
        action="store_true",
        help="Resume from previous incomplete setup",
    )
    setup_parser.add_argument(
        "--clear-state",
        action="store_true",
        help="Clear any existing setup state before starting",
    )

    # run-step command - execute individual steps
    run_step_parser = subparsers.add_parser(
        "run-step",
        help="Run a single setup step independently",
        description="""
Execute a single setup step. Steps can be specified by name or number.

Available steps:
  1. validate          - Validate demo folder structure and configuration
  2. create_lakehouse  - Create Lakehouse resource
  3. upload_files      - Upload CSV files to Lakehouse
  4. load_tables       - Load CSV files into Delta tables
  5. create_eventhouse - Create Eventhouse resource
  6. ingest_data       - Upload and ingest eventhouse data
  7. create_ontology   - Create ontology with entities and relationships
  8. bind_static       - Bind lakehouse properties (static data)
  9. bind_timeseries   - Bind eventhouse properties (timeseries data)
  10. bind_relationships - Bind relationship contextualizations
  11. verify           - Verify all bindings and resources in Fabric
  12. refresh_graph    - Refresh the ontology graph to sync bound data
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    run_step_parser.add_argument(
        "demo_path",
        type=str,
        help="Path to the demo folder",
    )
    run_step_parser.add_argument(
        "--step", "-s",
        type=str,
        required=True,
        help="Step to run (name like 'create_lakehouse' or number like '2')",
    )
    run_step_parser.add_argument(
        "--workspace-id", "-w",
        type=str,
        help="Fabric workspace ID (overrides config/env)",
    )
    run_step_parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force re-run even if step was previously completed",
    )

    # status command
    status_parser = subparsers.add_parser(
        "status",
        help="Check demo resource status",
    )
    status_parser.add_argument(
        "demo_path",
        type=str,
        help="Path to the demo folder",
    )
    status_parser.add_argument(
        "--workspace-id", "-w",
        type=str,
        help="Fabric workspace ID",
    )
    status_parser.add_argument(
        "--output-format", "-o",
        type=str,
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )

    # cleanup command
    cleanup_parser = subparsers.add_parser(
        "cleanup",
        help="Remove demo resources",
    )
    cleanup_parser.add_argument(
        "demo_path",
        type=str,
        help="Path to the demo folder",
    )
    cleanup_parser.add_argument(
        "--workspace-id", "-w",
        type=str,
        help="Fabric workspace ID",
    )
    cleanup_parser.add_argument(
        "--confirm",
        action="store_true",
        help="Confirm deletion (required)",
    )

    return parser


def run_init(args: argparse.Namespace) -> int:
    """Create demo.yaml template."""
    demo_path = Path(args.demo_path).resolve()

    if not demo_path.is_dir():
        console.print(f"[red]Error:[/red] Directory not found: {demo_path}")
        return 1

    config_file = demo_path / "demo.yaml"
    if config_file.exists() and not args.force:
        console.print(f"[yellow]Warning:[/yellow] demo.yaml already exists. Use --force to overwrite.")
        return 1

    template = generate_demo_yaml_template(demo_path)

    with open(config_file, "w", encoding="utf-8") as f:
        f.write(template)

    console.print(f"[green]✓[/green] Created {config_file}")
    console.print("\nNext steps:")
    console.print("  1. Set FABRIC_WORKSPACE_ID environment variable, or")
    console.print("  2. Edit demo.yaml and set fabric.workspace_id")
    console.print(f"  3. Run: fabric-demo validate {demo_path}")

    return 0


def run_validate(args: argparse.Namespace) -> int:
    """Validate demo package."""
    from .validator import DemoPackageValidator, ValidationSeverity
    
    demo_path = Path(args.demo_path).resolve()

    if not demo_path.is_dir():
        console.print(f"[red]Error:[/red] Directory not found: {demo_path}")
        return 1

    console.print(f"Validating demo package: [cyan]{demo_path.name}[/cyan]")

    try:
        # Run deep validation
        validator = DemoPackageValidator(demo_path)
        validation_result = validator.validate()
        
        # Load config for summary
        config = DemoConfiguration.from_demo_folder(demo_path)
        config_errors = config.validate()

        if config_errors:
            console.print("\n[red]Configuration errors:[/red]")
            for error in config_errors:
                console.print(f"  • {error}")
            return 1

        # Print validation summary
        table = Table(title="Demo Package Summary")
        table.add_column("Property", style="cyan")
        table.add_column("Value")

        table.add_row("Name", config.name)
        table.add_row("Workspace ID", config.fabric.workspace_id or "[yellow]Not set[/yellow]")
        table.add_row("Lakehouse Name", config.resources.lakehouse.name)
        table.add_row("Eventhouse Name", config.resources.eventhouse.name)
        table.add_row("Ontology Name", config.resources.ontology.name)

        # Data files
        lakehouse_files = config.get_lakehouse_csv_files()
        eventhouse_files = config.get_eventhouse_csv_files()
        table.add_row("Lakehouse CSV Files", str(len(lakehouse_files)))
        table.add_row("Eventhouse CSV Files", str(len(eventhouse_files)))

        # Ontology file
        if config.ontology_file:
            table.add_row("Ontology File", config.ontology_file.name)
        else:
            table.add_row("Ontology File", "[yellow]Not found[/yellow]")

        console.print(table)
        
        # Show detailed validation results
        show_details = getattr(args, 'show_details', False)
        
        if validation_result.issues:
            # Always show errors and warnings
            errors = [i for i in validation_result.issues if i.severity == ValidationSeverity.ERROR]
            warnings = [i for i in validation_result.issues if i.severity == ValidationSeverity.WARNING]
            infos = [i for i in validation_result.issues if i.severity == ValidationSeverity.INFO]
            
            if errors:
                console.print("\n[red]Errors:[/red]")
                for issue in errors:
                    msg = f"  ✗ {issue.message}"
                    if issue.path:
                        msg += f" [dim]({issue.path})[/dim]"
                    console.print(msg)
                    if issue.suggestion:
                        console.print(f"    [dim]→ {issue.suggestion}[/dim]")
            
            if warnings:
                console.print("\n[yellow]Warnings:[/yellow]")
                for issue in warnings:
                    msg = f"  ⚠ {issue.message}"
                    if issue.path:
                        msg += f" [dim]({issue.path})[/dim]"
                    console.print(msg)
                    if issue.suggestion:
                        console.print(f"    [dim]→ {issue.suggestion}[/dim]")
            
            if show_details and infos:
                console.print("\n[blue]Details:[/blue]")
                for issue in infos:
                    msg = f"  ℹ {issue.message}"
                    if issue.path:
                        msg += f" [dim]({issue.path})[/dim]"
                    console.print(msg)
        
        # Summary line
        if validation_result.is_valid:
            console.print(f"\n[green]✓[/green] Validation passed ({validation_result.error_count} errors, {validation_result.warning_count} warnings)")
            if not show_details and validation_result.info_count > 0:
                console.print(f"  [dim]Use --show-details to see {validation_result.info_count} additional info messages[/dim]")
            return 0
        else:
            console.print(f"\n[red]✗[/red] Validation failed ({validation_result.error_count} errors)")
            return 1

    except ConfigurationError as e:
        console.print(f"\n[red]Configuration error:[/red] {e}")
        return 1
    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}")
        return 1


def run_setup(args: argparse.Namespace) -> int:
    """Run complete demo setup."""
    demo_path = Path(args.demo_path).resolve()

    if not demo_path.is_dir():
        console.print(f"[red]Error:[/red] Directory not found: {demo_path}")
        return 1

    console.print(Panel(f"Setting up demo: [bold cyan]{demo_path.name}[/bold cyan]"))

    try:
        # Load configuration
        config = DemoConfiguration.from_demo_folder(
            demo_path,
            workspace_id=args.workspace_id,
        )

        # Apply CLI overrides
        config.options.skip_existing = args.skip_existing
        config.options.dry_run = args.dry_run
        config.options.interactive = getattr(args, 'interactive', False)

        # Validate
        errors = config.validate()
        if errors:
            console.print("\n[red]Configuration errors:[/red]")
            for error in errors:
                console.print(f"  • {error}")
            return 1

        # Handle resume logic
        resume = getattr(args, 'resume', False)
        clear_state = getattr(args, 'clear_state', False)

        # Create orchestrator with resume flag
        orchestrator = DemoOrchestrator(config, resume=resume)

        # Clear state if requested
        if clear_state:
            orchestrator.clear_state()
            console.print("[yellow]Cleared existing setup state[/yellow]")

        # Check for resumable state
        if not resume and orchestrator.has_resumable_state():
            resume_summary = orchestrator.get_resume_summary()
            if resume_summary:
                console.print("\n[yellow]⚠ Previous incomplete setup detected:[/yellow]")
                console.print(f"  Started: {resume_summary.get('started_at', 'unknown')}")
                console.print(f"  Completed steps: {', '.join(resume_summary.get('completed_steps', [])) or 'none'}")
                
                if resume_summary.get('failed_step'):
                    console.print(f"  [red]Failed step: {resume_summary.get('failed_step')}[/red]")
                
                console.print("\n  Use [cyan]--resume[/cyan] to continue from where you left off")
                console.print("  Use [cyan]--clear-state[/cyan] to start fresh")
                
                response = console.input("\n[bold]Resume previous setup? [Y/n]:[/bold] ").strip().lower()
                if response in ("", "y", "yes"):
                    resume = True
                    orchestrator = DemoOrchestrator(config, resume=True)
                else:
                    orchestrator.clear_state()
                    console.print("[dim]Starting fresh...[/dim]")

        # Run setup
        results = orchestrator.run_setup(dry_run=args.dry_run)

        # Print results
        print_setup_results(results)

        # Check for failures
        failed = any(r.status.value == "failed" for r in results.values())
        if failed:
            console.print("\n[red]Setup completed with errors[/red]")
            console.print("[dim]Run with --resume to continue from the last successful step[/dim]")
            return 1

        console.print("\n[green]✓[/green] Demo setup completed successfully!")

        # Clear state on successful completion
        orchestrator.clear_state()

        # Print resource summary
        state = orchestrator.get_state()
        if state.lakehouse_id:
            console.print(f"  Lakehouse ID: {state.lakehouse_id}")
        if state.eventhouse_id:
            console.print(f"  Eventhouse ID: {state.eventhouse_id}")
        if state.ontology_id:
            console.print(f"  Ontology ID: {state.ontology_id}")

        return 0

    except DemoAutomationError as e:
        console.print(f"\n[red]Setup failed:[/red] {e}")
        console.print("[dim]Run with --resume to continue from the last successful step[/dim]")
        return 1
    except KeyboardInterrupt:
        console.print("\n[yellow]Setup cancelled by user[/yellow]")
        return 130
    except Exception as e:
        console.print(f"\n[red]Unexpected error:[/red] {e}")
        logging.exception("Setup failed")
        return 1


# Step mapping for run-step command (aligned with ResearchFixes.md 11 steps)
STEP_MAPPING = {
    "1": "validate",
    "2": "create_lakehouse",
    "3": "upload_files",
    "4": "load_tables",
    "5": "create_eventhouse",
    "6": "ingest_data",
    "7": "create_ontology",
    "8": "bind_static",
    "9": "bind_timeseries",
    "10": "bind_relationships",
    "11": "verify",
    "12": "refresh_graph",
    # Also allow step names directly
    "validate": "validate",
    "create_lakehouse": "create_lakehouse",
    "upload_files": "upload_files",
    "load_tables": "load_tables",
    "create_eventhouse": "create_eventhouse",
    "ingest_data": "ingest_data",
    "create_ontology": "create_ontology",
    "bind_static": "bind_static",
    "bind_timeseries": "bind_timeseries",
    "bind_relationships": "bind_relationships",
    "verify": "verify",
    "refresh_graph": "refresh_graph",
    # Legacy mapping for configure_bindings (runs all binding steps)
    "configure_bindings": "configure_bindings",
}


def run_step(args: argparse.Namespace) -> int:
    """Run a single setup step independently."""
    demo_path = Path(args.demo_path).resolve()

    if not demo_path.is_dir():
        console.print(f"[red]Error:[/red] Directory not found: {demo_path}")
        return 1

    step_input = args.step.lower()
    step_name = STEP_MAPPING.get(step_input)
    
    if not step_name:
        console.print(f"[red]Error:[/red] Unknown step: {args.step}")
        console.print("\nValid steps (by number or name):")
        console.print("  1. validate          - Validate demo folder structure")
        console.print("  2. create_lakehouse  - Create Lakehouse resource")
        console.print("  3. upload_files      - Upload CSV files to Lakehouse")
        console.print("  4. load_tables       - Load CSV files into Delta tables")
        console.print("  5. create_eventhouse - Create Eventhouse resource")
        console.print("  6. ingest_data       - Upload and ingest eventhouse data")
        console.print("  7. create_ontology   - Create ontology with entities")
        console.print("  8. bind_static       - Bind lakehouse properties (static)")
        console.print("  9. bind_timeseries   - Bind eventhouse properties (timeseries)")
        console.print("  10. bind_relationships - Bind relationship contextualizations")
        console.print("  11. verify           - Verify all resources and bindings")
        console.print("  12. refresh_graph    - Refresh ontology graph to sync data")
        return 1

    console.print(Panel(f"Running step: [bold cyan]{step_name}[/bold cyan]"))

    try:
        # Load configuration
        config = DemoConfiguration.from_demo_folder(
            demo_path,
            workspace_id=args.workspace_id,
        )

        errors = config.validate()
        if errors and step_name != "validate":
            console.print("\n[red]Configuration errors:[/red]")
            for error in errors:
                console.print(f"  • {error}")
            return 1

        # Create orchestrator (always resume to load existing state)
        orchestrator = DemoOrchestrator(config, resume=True)

        # Check if step was already completed
        force = getattr(args, 'force', False)
        if not force and orchestrator._state_manager.is_step_completed(step_name):
            console.print(f"[yellow]Step '{step_name}' already completed.[/yellow]")
            console.print("  Use [cyan]--force[/cyan] to re-run")
            return 0

        # If forcing, reset this step's state
        if force and orchestrator._state_manager.is_step_completed(step_name):
            console.print(f"[dim]Force flag set, re-running step...[/dim]")

        # Run the specific step
        result = orchestrator.run_single_step(step_name)

        # Print result
        if result.status.value == "completed":
            console.print(f"\n[green]✓[/green] Step completed: {result.message}")
            if result.artifact_id:
                console.print(f"  Artifact ID: {result.artifact_id}")
            return 0
        elif result.status.value == "skipped":
            console.print(f"\n[yellow]○[/yellow] Step skipped: {result.message}")
            return 0
        else:
            console.print(f"\n[red]✗[/red] Step failed: {result.message}")
            return 1

    except DemoAutomationError as e:
        console.print(f"\n[red]Error:[/red] {e}")
        return 1
    except Exception as e:
        console.print(f"\n[red]Unexpected error:[/red] {e}")
        logging.exception(f"Step {step_name} failed")
        return 1


def run_status(args: argparse.Namespace) -> int:
    """Check demo resource status with 11-step progress tracking."""
    from rich.progress import Progress, BarColumn, TextColumn, TaskProgressColumn
    
    demo_path = Path(args.demo_path).resolve()

    if not demo_path.is_dir():
        console.print(f"[red]Error:[/red] Directory not found: {demo_path}")
        return 1

    # Define the 12 steps from ResearchFixes.md (aligned with task requirements)
    # Steps 8-10 are separate binding steps for static, timeseries, and relationships
    # Step 12 is the graph refresh step added after verification
    SETUP_STEPS = [
        ("validate", "1. Validate", "Validate demo folder structure"),
        ("create_lakehouse", "2. Lakehouse", "Create Lakehouse resource"),
        ("upload_files", "3. Upload", "Upload lakehouse CSV files"),
        ("load_tables", "4. Tables", "Load CSV to Delta tables"),
        ("create_eventhouse", "5. Eventhouse", "Create Eventhouse resource"),
        ("ingest_data", "6. Ingest", "Ingest data to KQL tables"),
        ("create_ontology", "7. Ontology", "Create ontology with entities"),
        ("bind_static", "8. Static", "Bind lakehouse properties"),
        ("bind_timeseries", "9. Timeseries", "Bind eventhouse properties"),
        ("bind_relationships", "10. Relations", "Bind relationship contextualizations"),
        ("verify", "11. Verify", "Validate all bindings in Fabric"),
        ("refresh_graph", "12. Refresh", "Refresh ontology graph to sync data"),
    ]
    
    # Also check for legacy configure_bindings step (maps to bind_static+bind_timeseries+bind_relationships)
    LEGACY_BINDING_STEP = "configure_bindings"

    try:
        config = DemoConfiguration.from_demo_folder(
            demo_path,
            workspace_id=args.workspace_id,
        )

        errors = config.validate()
        if errors:
            console.print(f"[red]Configuration error:[/red] {errors[0]}")
            return 1

        console.print(Panel(f"Status: [bold cyan]{config.name}[/bold cyan]"))

        # Check for setup state file
        from .state_manager import SetupStateManager, StepStatus as PersistentStepStatus
        
        state_manager = SetupStateManager(
            demo_path=config.demo_path,
            workspace_id=config.fabric.workspace_id,
            demo_name=config.name,
        )

        # Load state if exists
        setup_state = None
        if state_manager.has_existing_state():
            setup_state = state_manager.load_state()

        # Calculate step completion
        completed_steps = []
        failed_step = None
        in_progress_step = None
        
        if setup_state:
            completed_steps = setup_state.get_completed_steps()
            failed_step = setup_state.get_failed_step()
            for step_id, step in setup_state.steps.items():
                if step.status == PersistentStepStatus.IN_PROGRESS:
                    in_progress_step = step_id
                    break
            
            # Handle legacy configure_bindings step - if completed, mark all 3 binding steps as completed
            if LEGACY_BINDING_STEP in completed_steps:
                completed_steps.extend(["bind_static", "bind_timeseries", "bind_relationships"])

        # Build step status table
        step_table = Table(title="Setup Progress (11 Steps)", show_header=True)
        step_table.add_column("#", style="dim", width=3)
        step_table.add_column("Step", style="cyan", width=12)
        step_table.add_column("Status", width=15)
        step_table.add_column("Details", style="dim")

        completed_count = 0
        
        for step_id, step_name, step_desc in SETUP_STEPS:
            # Check if step is completed (direct or via legacy configure_bindings)
            is_completed = step_id in completed_steps
            
            if is_completed:
                status = "[green]✓ Completed[/green]"
                completed_count += 1
                # Get artifact info if available
                details = ""
                # Check direct step or legacy binding step for details
                check_step_id = step_id
                if step_id in ("bind_static", "bind_timeseries", "bind_relationships"):
                    check_step_id = LEGACY_BINDING_STEP if LEGACY_BINDING_STEP in (setup_state.steps if setup_state else {}) else step_id
                
                if setup_state and check_step_id in setup_state.steps:
                    step_state = setup_state.steps[check_step_id]
                    if step_state.artifact_name:
                        details = step_state.artifact_name
                    elif step_state.details:
                        if "loaded" in step_state.details:
                            details = f"{len(step_state.details['loaded'])} tables"
                        elif "uploaded" in step_state.details:
                            details = f"{len(step_state.details['uploaded'])} files"
                        elif "lakehouse_bindings" in step_state.details:
                            details = f"{step_state.details.get('lakehouse_bindings', 0)} bindings"
            elif step_id == failed_step:
                status = "[red]✗ Failed[/red]"
                details = ""
                if setup_state and step_id in setup_state.steps:
                    details = setup_state.steps[step_id].error_message or ""
            elif step_id == in_progress_step:
                status = "[yellow]◐ In Progress[/yellow]"
                details = ""
            else:
                status = "[dim]○ Pending[/dim]"
                details = ""
            
            step_num = step_name.split(".")[0]
            step_label = step_name.split(". ")[1] if ". " in step_name else step_name
            step_table.add_row(step_num, step_label, status, details[:40])

        console.print(step_table)

        # Progress bar
        total_steps = len(SETUP_STEPS)
        progress_pct = (completed_count / total_steps) * 100
        
        # Visual progress bar
        bar_width = 40
        filled = int(bar_width * completed_count / total_steps)
        bar = "█" * filled + "░" * (bar_width - filled)
        
        if completed_count == total_steps:
            color = "green"
            status_text = "COMPLETE"
        elif failed_step:
            color = "red"
            status_text = "FAILED"
        elif in_progress_step:
            color = "yellow"
            status_text = "IN PROGRESS"
        else:
            color = "cyan"
            status_text = "NOT STARTED"
        
        console.print(f"\n[{color}]Progress: [{bar}] {progress_pct:.0f}% ({completed_count}/{total_steps} steps) - {status_text}[/{color}]")

        # Show setup state info if available
        if setup_state:
            console.print(f"\n[dim]Setup ID: {setup_state.setup_id[:8]}...[/dim]")
            console.print(f"[dim]Started: {setup_state.started_at}[/dim]")
            if setup_state.completed_at:
                console.print(f"[dim]Completed: {setup_state.completed_at}[/dim]")
        
        # Resource status table
        console.print("\n")
        from .platform import FabricClient

        with FabricClient(
            workspace_id=config.fabric.workspace_id,
            tenant_id=config.fabric.tenant_id,
        ) as client:
            resource_table = Table(title="Fabric Resources")
            resource_table.add_column("Resource", style="cyan")
            resource_table.add_column("Status")
            resource_table.add_column("ID", style="dim")
            resource_table.add_column("Tables/Entities", style="dim")

            # Check Lakehouse
            lh = client.find_lakehouse_by_name(config.resources.lakehouse.name)
            if lh:
                lh_id = lh.get("id", "")
                # Try to get table count
                table_info = ""
                try:
                    from .platform import LakehouseClient
                    lh_client = LakehouseClient(fabric_client=client, workspace_id=config.fabric.workspace_id)
                    tables = lh_client.list_tables(lh_id)
                    table_info = f"{len(tables)} tables"
                except Exception:
                    table_info = "-"
                resource_table.add_row(
                    f"Lakehouse: {config.resources.lakehouse.name}",
                    "[green]✓ Exists[/green]",
                    lh_id[:12] + "..." if len(lh_id) > 12 else lh_id,
                    table_info,
                )
            else:
                resource_table.add_row(
                    f"Lakehouse: {config.resources.lakehouse.name}",
                    "[yellow]○ Not found[/yellow]",
                    "-",
                    "-",
                )

            # Check Eventhouse
            eh = client.find_eventhouse_by_name(config.resources.eventhouse.name)
            if eh:
                eh_id = eh.get("id", "")
                resource_table.add_row(
                    f"Eventhouse: {config.resources.eventhouse.name}",
                    "[green]✓ Exists[/green]",
                    eh_id[:12] + "..." if len(eh_id) > 12 else eh_id,
                    "-",
                )
            else:
                resource_table.add_row(
                    f"Eventhouse: {config.resources.eventhouse.name}",
                    "[yellow]○ Not found[/yellow]",
                    "-",
                    "-",
                )

            # Check Ontology
            ont = client.find_ontology_by_name(config.resources.ontology.name)
            if ont:
                ont_id = ont.get("id", "")
                # Try to get entity count
                entity_info = ""
                try:
                    ont_def = client.get_ontology_definition(ont_id)
                    parts = ont_def.get("definition", {}).get("parts", [])
                    entity_count = sum(1 for p in parts if "EntityTypes/" in p.get("path", "") and p.get("path", "").endswith(".json"))
                    binding_count = sum(1 for p in parts if "DataBindings" in p.get("path", ""))
                    entity_info = f"{entity_count} entities, {binding_count} bindings"
                except Exception:
                    entity_info = "-"
                resource_table.add_row(
                    f"Ontology: {config.resources.ontology.name}",
                    "[green]✓ Exists[/green]",
                    ont_id[:12] + "..." if len(ont_id) > 12 else ont_id,
                    entity_info,
                )
            else:
                resource_table.add_row(
                    f"Ontology: {config.resources.ontology.name}",
                    "[yellow]○ Not found[/yellow]",
                    "-",
                    "-",
                )

            console.print(resource_table)

        # Actionable next steps
        if failed_step:
            console.print(f"\n[red]⚠ Setup failed at step: {failed_step}[/red]")
            console.print("  Run [cyan]fabric-demo setup {path} --resume[/cyan] to retry from this step")
        elif completed_count == 0:
            console.print("\n[dim]Run [cyan]fabric-demo setup {path}[/cyan] to start setup[/dim]")
        elif completed_count < total_steps:
            console.print(f"\n[yellow]Setup incomplete ({total_steps - completed_count} steps remaining)[/yellow]")
            console.print("  Run [cyan]fabric-demo setup {path} --resume[/cyan] to continue")

        return 0

    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}")
        return 1


def run_cleanup(args: argparse.Namespace) -> int:
    """Remove demo resources."""
    demo_path = Path(args.demo_path).resolve()

    if not demo_path.is_dir():
        console.print(f"[red]Error:[/red] Directory not found: {demo_path}")
        return 1

    if not args.confirm:
        console.print("[yellow]Warning:[/yellow] This will delete all demo resources.")
        console.print("Use --confirm to proceed.")
        return 1

    try:
        config = DemoConfiguration.from_demo_folder(
            demo_path,
            workspace_id=args.workspace_id,
        )

        errors = config.validate()
        if errors:
            console.print(f"[red]Configuration error:[/red] {errors[0]}")
            return 1

        from .platform import FabricClient

        with FabricClient(
            workspace_id=config.fabric.workspace_id,
            tenant_id=config.fabric.tenant_id,
        ) as client:
            console.print(Panel(f"Cleaning up demo: [bold red]{config.name}[/bold red]"))

            # Delete Ontology first (depends on data sources)
            ont = client.find_ontology_by_name(config.resources.ontology.name)
            if ont:
                console.print(f"Deleting Ontology: {config.resources.ontology.name}")
                client.delete_ontology(ont["id"])
                console.print("[green]  ✓ Deleted[/green]")

            # Delete Eventhouse
            eh = client.find_eventhouse_by_name(config.resources.eventhouse.name)
            if eh:
                console.print(f"Deleting Eventhouse: {config.resources.eventhouse.name}")
                client.delete_eventhouse(eh["id"])
                console.print("[green]  ✓ Deleted[/green]")

            # Delete Lakehouse
            lh = client.find_lakehouse_by_name(config.resources.lakehouse.name)
            if lh:
                console.print(f"Deleting Lakehouse: {config.resources.lakehouse.name}")
                client.delete_lakehouse(lh["id"])
                console.print("[green]  ✓ Deleted[/green]")

        console.print("\n[green]✓[/green] Cleanup completed")
        return 0

    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}")
        return 1


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    setup_logging(args.verbose)

    commands = {
        "init": run_init,
        "validate": run_validate,
        "setup": run_setup,
        "run-step": run_step,
        "status": run_status,
        "cleanup": run_cleanup,
    }

    handler = commands.get(args.command)
    if handler:
        return handler(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
