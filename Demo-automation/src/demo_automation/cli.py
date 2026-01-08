"""
Command-line interface for Fabric Demo Automation.

Provides commands for:
- config: Manage global configuration
- init: Create demo.yaml template
- validate: Validate demo package structure
- setup: Run complete demo setup
- status: Check demo resource status
- list: List demos in workspace
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
from rich.prompt import Prompt, Confirm

from .core.config import DemoConfiguration, generate_demo_yaml_template
from .core.global_config import GlobalConfig, get_config_file_path, config_file_exists, generate_config_template
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
        prog="demo_automation",
        description="Fabric Ontology Demo Automation Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage: python -m demo_automation <command> [options]

Examples:
  # First-time setup
  python -m demo_automation config init                     # Configure workspace ID
  
  # Working with demos
  python -m demo_automation validate ./MedicalManufacturing
  python -m demo_automation setup ./MedicalManufacturing
  python -m demo_automation status ./MedicalManufacturing
  python -m demo_automation list                            # List demos in workspace
  python -m demo_automation cleanup ./MedicalManufacturing
  
  # Advanced usage
  python -m demo_automation setup ./Demo --workspace-id abc  # Override workspace
  python -m demo_automation run-step ./Demo --step 8         # Run single step
  python -m demo_automation cleanup ./Demo --force-by-name   # Cleanup without state file
        """,
    )

    # Global options
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output with full stack traces",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # config command
    config_parser = subparsers.add_parser(
        "config",
        help="Manage global configuration",
        description="View or modify global fabric-demo settings.",
    )
    config_subparsers = config_parser.add_subparsers(dest="config_action", help="Config actions")
    
    # config init
    config_init_parser = config_subparsers.add_parser(
        "init",
        help="Initialize global configuration interactively",
    )
    config_init_parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Overwrite existing configuration",
    )
    
    # config show
    config_subparsers.add_parser(
        "show",
        help="Show current configuration",
    )
    
    # config path
    config_subparsers.add_parser(
        "path",
        help="Show configuration file path",
    )

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
        description="""
Remove demo resources from your Fabric workspace.

By default, cleanup uses the state file (.setup-state.yaml) to identify exactly
which resources were created, preventing accidental deletion.

If the state file is missing, use --force-by-name to delete resources by name.
        """,
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
        "--confirm", "--yes", "-y",
        action="store_true",
        help="Skip confirmation prompt",
    )
    cleanup_parser.add_argument(
        "--force-by-name",
        action="store_true",
        help="Delete resources by name even without state file (use with caution)",
    )

    # list command
    list_parser = subparsers.add_parser(
        "list",
        help="List demo resources in workspace",
        description="List ontologies, lakehouses, and eventhouses in your Fabric workspace.",
    )
    list_parser.add_argument(
        "--workspace-id", "-w",
        type=str,
        help="Fabric workspace ID",
    )
    list_parser.add_argument(
        "--filter", "-f",
        type=str,
        help="Filter resources by name pattern",
    )

    # docs command
    subparsers.add_parser(
        "docs",
        help="Open documentation in browser",
        description="Open the fabric-demo documentation in your default browser.",
    )

    # recover command
    recover_parser = subparsers.add_parser(
        "recover",
        help="Recover state file from existing Fabric resources",
        description="""
Rebuild the state file by discovering existing resources in Fabric.

Use this when the .setup-state.yaml file is lost but resources still exist.
The command searches for resources matching the demo naming convention and
recreates the state file so cleanup and other commands work correctly.
        """,
    )
    recover_parser.add_argument(
        "demo_path",
        type=str,
        help="Path to the demo folder",
    )
    recover_parser.add_argument(
        "--workspace-id", "-w",
        type=str,
        help="Fabric workspace ID",
    )
    recover_parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Overwrite existing state file",
    )

    return parser


def run_config(args: argparse.Namespace) -> int:
    """Manage global configuration."""
    action = getattr(args, 'config_action', None)
    
    if action == "init":
        return _config_init(args)
    elif action == "show":
        return _config_show()
    elif action == "path":
        return _config_path()
    else:
        # No subcommand - show help
        console.print("Usage: fabric-demo config <init|show|path>")
        console.print("\nActions:")
        console.print("  init   Initialize configuration interactively")
        console.print("  show   Show current configuration")
        console.print("  path   Show configuration file path")
        return 0


def _config_init(args: argparse.Namespace) -> int:
    """Initialize global configuration interactively."""
    config_path = get_config_file_path()
    
    if config_file_exists() and not getattr(args, 'force', False):
        console.print(f"[yellow]Configuration file already exists:[/yellow] {config_path}")
        if not Confirm.ask("Overwrite existing configuration?"):
            return 0
    
    console.print(Panel("[bold cyan]Fabric Demo Configuration Setup[/bold cyan]"))
    console.print("This will create a global configuration file for fabric-demo.\n")
    
    # Get workspace ID
    workspace_id = Prompt.ask(
        "Enter your Fabric workspace ID (GUID)",
        default="",
    )
    
    # Get tenant ID (optional)
    tenant_id = Prompt.ask(
        "Enter your Azure tenant ID (optional, press Enter to skip)",
        default="",
    )
    
    # Get auth method
    console.print("\nAuthentication methods:")
    console.print("  [cyan]1[/cyan] - interactive (Opens browser for login - recommended)")
    console.print("  [cyan]2[/cyan] - service_principal (Uses environment variables)")
    console.print("  [cyan]3[/cyan] - default (Azure SDK default chain)")
    auth_choice = Prompt.ask(
        "Select authentication method",
        choices=["1", "2", "3"],
        default="1",
    )
    auth_method_map = {"1": "interactive", "2": "service_principal", "3": "default"}
    auth_method = auth_method_map[auth_choice]
    
    # Create and save config
    config = GlobalConfig(
        workspace_id=workspace_id if workspace_id else None,
        tenant_id=tenant_id if tenant_id else None,
        auth_method=auth_method,
    )
    config.save()
    
    console.print(f"\n[green]✓[/green] Configuration saved to {config_path}")
    
    if not workspace_id:
        console.print("\n[yellow]Note:[/yellow] No workspace ID configured.")
        console.print("You can set it later via:")
        console.print("  • Environment variable: FABRIC_WORKSPACE_ID=<your-id>")
        console.print("  • CLI argument: --workspace-id <your-id>")
        console.print("  • Edit config file directly")
    
    return 0


def _config_show() -> int:
    """Show current configuration."""
    config = GlobalConfig.load()
    
    table = Table(title="Fabric Demo Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value")
    table.add_column("Source", style="dim")
    
    # Determine source for each value
    import os
    ws_source = "env" if os.environ.get('FABRIC_WORKSPACE_ID') else ("config" if config.workspace_id else "not set")
    tenant_source = "env" if os.environ.get('AZURE_TENANT_ID') else ("config" if config.tenant_id else "not set")
    
    table.add_row("Workspace ID", config.workspace_id or "[dim]not set[/dim]", ws_source)
    table.add_row("Tenant ID", config.tenant_id or "[dim]not set[/dim]", tenant_source)
    table.add_row("Auth Method", config.auth_method, "config")
    table.add_row("Skip Existing", str(config.skip_existing), "config")
    table.add_row("Confirm Cleanup", str(config.confirm_cleanup), "config")
    table.add_section()
    table.add_row("[bold]Rate Limiting[/bold]", "", "")
    table.add_row("  Enabled", str(config.rate_limit_enabled), "config")
    table.add_row("  Requests/min", str(config.rate_limit_requests_per_minute), "config")
    table.add_row("  Burst", str(config.rate_limit_burst), "config")
    
    console.print(table)
    
    config_path = get_config_file_path()
    if config_file_exists():
        console.print(f"\n[dim]Config file: {config_path}[/dim]")
    else:
        console.print(f"\n[dim]No config file. Run 'fabric-demo config init' to create one.[/dim]")
    
    return 0


def _config_path() -> int:
    """Show configuration file path."""
    config_path = get_config_file_path()
    console.print(f"Config file: {config_path}")
    if config_file_exists():
        console.print("[green]✓[/green] File exists")
    else:
        console.print("[yellow]File does not exist[/yellow]")
        console.print("Run 'fabric-demo config init' to create it.")
    return 0


def run_docs(args: argparse.Namespace) -> int:
    """Open documentation in browser."""
    import webbrowser
    from pathlib import Path
    
    # Try to find the docs folder relative to this file
    # The structure is: Demo-automation/src/demo_automation/cli.py
    # Docs are at: docs/index.md (relative to repo root)
    
    # First, check for GitHub docs URL (preferred for users)
    github_docs_url = "https://github.com/falloutxAY/Fabric-Ontology-demoAgent/blob/main/docs/index.md"
    
    # Try to find local docs
    cli_path = Path(__file__).resolve()
    repo_root = cli_path.parent.parent.parent.parent.parent  # Go up from cli.py
    local_docs = repo_root / "docs" / "index.md"
    
    if local_docs.exists():
        # Open local docs if available
        local_url = local_docs.as_uri()
        console.print(f"Opening local documentation: {local_docs}")
        webbrowser.open(local_url)
    else:
        # Fall back to GitHub
        console.print(f"Opening documentation on GitHub...")
        webbrowser.open(github_docs_url)
    
    console.print("[green]✓[/green] Documentation opened in browser")
    return 0


def run_recover(args: argparse.Namespace) -> int:
    """Recover state file from existing Fabric resources."""
    from pathlib import Path
    from .platform import FabricClient
    from .state_manager import SetupStateManager
    from .core.config import DemoConfiguration
    
    demo_path = Path(args.demo_path).resolve()
    
    if not demo_path.exists():
        console.print(f"[red]Error:[/red] Demo folder not found: {demo_path}")
        return 1
    
    # Check for existing state file
    state_file = demo_path / ".setup-state.yaml"
    if state_file.exists() and not getattr(args, 'force', False):
        console.print(f"[yellow]State file already exists:[/yellow] {state_file}")
        console.print("Use --force to overwrite.")
        return 1
    
    # Load global config
    global_config = GlobalConfig.load()
    workspace_id = global_config.get_workspace_id(getattr(args, 'workspace_id', None))
    
    if not workspace_id:
        console.print("[red]Error:[/red] No workspace ID configured.")
        console.print("\nSet workspace ID via one of:")
        console.print("  • fabric-demo config init")
        console.print("  • Environment variable: FABRIC_WORKSPACE_ID")
        console.print("  • CLI argument: --workspace-id")
        return 1
    
    # Try to load demo config for name
    try:
        config = DemoConfiguration.from_demo_path(demo_path)
        demo_name = config.name
    except Exception:
        # Fall back to folder name
        demo_name = demo_path.name
    
    console.print(f"[bold]Recovering state for:[/bold] {demo_name}")
    console.print(f"[dim]Workspace: {workspace_id}[/dim]\n")
    
    try:
        with FabricClient(
            workspace_id=workspace_id,
            tenant_id=global_config.tenant_id,
        ) as client:
            discovered = {}
            
            # Search for Lakehouse
            console.print("Searching for Lakehouse...", end=" ")
            lakehouses = client.list_lakehouses()
            for lh in lakehouses:
                if lh.get('displayName', '').startswith(demo_name):
                    discovered["lakehouse"] = {
                        "id": lh.get('id'),
                        "name": lh.get('displayName'),
                    }
                    console.print(f"[green]Found: {lh.get('displayName')}[/green]")
                    break
            else:
                console.print("[dim]Not found[/dim]")
            
            # Search for Eventhouse
            console.print("Searching for Eventhouse...", end=" ")
            eventhouses = client.list_eventhouses()
            for eh in eventhouses:
                if eh.get('displayName', '').startswith(demo_name):
                    discovered["eventhouse"] = {
                        "id": eh.get('id'),
                        "name": eh.get('displayName'),
                    }
                    console.print(f"[green]Found: {eh.get('displayName')}[/green]")
                    break
            else:
                console.print("[dim]Not found[/dim]")
            
            # Search for KQL Database (separate from eventhouse)
            console.print("Searching for KQL Database...", end=" ")
            try:
                kql_dbs = client.list_kql_databases()
                for db in kql_dbs:
                    if db.get('displayName', '').startswith(demo_name):
                        discovered["kql_database"] = {
                            "id": db.get('id'),
                            "name": db.get('displayName'),
                        }
                        console.print(f"[green]Found: {db.get('displayName')}[/green]")
                        break
                else:
                    console.print("[dim]Not found[/dim]")
            except Exception:
                console.print("[dim]Not found[/dim]")
            
            # Search for Ontology
            console.print("Searching for Ontology...", end=" ")
            ontologies = client.list_ontologies()
            for ont in ontologies:
                if ont.get('displayName', '').startswith(demo_name):
                    discovered["ontology"] = {
                        "id": ont.get('id'),
                        "name": ont.get('displayName'),
                    }
                    console.print(f"[green]Found: {ont.get('displayName')}[/green]")
                    break
            else:
                console.print("[dim]Not found[/dim]")
            
            if not discovered:
                console.print("\n[yellow]No matching resources found in workspace.[/yellow]")
                console.print("Make sure resources follow the naming convention (prefixed with demo name).")
                return 1
            
            # Create recovered state
            console.print("\nCreating state file...", end=" ")
            SetupStateManager.recover_from_fabric(
                demo_path=demo_path,
                workspace_id=workspace_id,
                demo_name=demo_name,
                discovered_resources=discovered,
            )
            console.print("[green]Done[/green]")
            
            # Show summary
            console.print("\n[bold green]✓ State recovered successfully[/bold green]")
            console.print("\nRecovered resources:")
            for resource_type, info in discovered.items():
                console.print(f"  • {resource_type}: {info['name']} [dim]({info['id']})[/dim]")
            
            console.print(f"\n[dim]State file: {state_file}[/dim]")
            console.print("\nYou can now use:")
            console.print("  • fabric-demo status <path>  - View status")
            console.print("  • fabric-demo cleanup <path> - Clean up resources")
            
            return 0
            
    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}")
        if getattr(args, 'debug', False):
            import traceback
            console.print(traceback.format_exc())
        return 1


def run_list(args: argparse.Namespace) -> int:
    """List demo resources in workspace."""
    from .platform import FabricClient
    
    # Load global config
    global_config = GlobalConfig.load()
    workspace_id = global_config.get_workspace_id(getattr(args, 'workspace_id', None))
    
    if not workspace_id:
        console.print("[red]Error:[/red] No workspace ID configured.")
        console.print("\nSet workspace ID via one of:")
        console.print("  • fabric-demo config init")
        console.print("  • Environment variable: FABRIC_WORKSPACE_ID")
        console.print("  • CLI argument: --workspace-id")
        return 1
    
    filter_pattern = getattr(args, 'filter', None)
    
    try:
        with FabricClient(
            workspace_id=workspace_id,
            tenant_id=global_config.tenant_id,
        ) as client:
            console.print(f"Listing resources in workspace: [cyan]{workspace_id}[/cyan]\n")
            
            # List Ontologies
            ontologies = client.list_ontologies()
            if filter_pattern:
                ontologies = [o for o in ontologies if filter_pattern.lower() in o.get('displayName', '').lower()]
            
            console.print("[bold]Ontologies[/bold]")
            if ontologies:
                for ont in ontologies:
                    name = ont.get('displayName', 'Unknown')
                    ont_id = ont.get('id', '')
                    console.print(f"  • {name} [dim]({ont_id})[/dim]")
            else:
                console.print("  [dim]No ontologies found[/dim]")
            
            # List Lakehouses
            console.print("\n[bold]Lakehouses[/bold]")
            lakehouses = client.list_lakehouses()
            if filter_pattern:
                lakehouses = [l for l in lakehouses if filter_pattern.lower() in l.get('displayName', '').lower()]
            
            if lakehouses:
                for lh in lakehouses:
                    name = lh.get('displayName', 'Unknown')
                    lh_id = lh.get('id', '')
                    console.print(f"  • {name} [dim]({lh_id})[/dim]")
            else:
                console.print("  [dim]No lakehouses found[/dim]")
            
            # List Eventhouses
            console.print("\n[bold]Eventhouses[/bold]")
            eventhouses = client.list_eventhouses()
            if filter_pattern:
                eventhouses = [e for e in eventhouses if filter_pattern.lower() in e.get('displayName', '').lower()]
            
            if eventhouses:
                for eh in eventhouses:
                    name = eh.get('displayName', 'Unknown')
                    eh_id = eh.get('id', '')
                    console.print(f"  • {name} [dim]({eh_id})[/dim]")
            else:
                console.print("  [dim]No eventhouses found[/dim]")
        
        return 0
    
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        return 1


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
    """Remove demo resources that were created by setup.
    
    Uses the state file to identify exactly which resources were created,
    preventing accidental deletion of pre-existing resources.
    
    If --force-by-name is used, deletes by resource name (when state file missing).
    """
    demo_path = Path(args.demo_path).resolve()

    if not demo_path.is_dir():
        console.print(f"[red]Error:[/red] Directory not found: {demo_path}")
        return 1

    # Load global config for defaults
    global_config = GlobalConfig.load()
    
    # Check for state file first
    from .state_manager import SetupStateManager, STATE_FILE_NAME
    
    state_file = demo_path / STATE_FILE_NAME
    force_by_name = getattr(args, 'force_by_name', False)
    
    if not state_file.exists() and not force_by_name:
        console.print(f"[yellow]Warning:[/yellow] No state file found at {state_file}")
        console.print("This means no resources were created by setup, or state was already cleared.")
        console.print("\n[dim]If you want to delete resources by name anyway, use:[/dim]")
        console.print(f"  fabric-demo cleanup {args.demo_path} --force-by-name")
        return 0

    try:
        # Resolve workspace ID
        workspace_id = global_config.get_workspace_id(getattr(args, 'workspace_id', None))
        
        config = DemoConfiguration.from_demo_folder(
            demo_path,
            workspace_id=workspace_id,
        )

        errors = config.validate()
        if errors:
            console.print(f"[red]Configuration error:[/red] {errors[0]}")
            return 1

        from .platform import FabricClient

        # Determine what to delete
        resources_to_delete = []
        state_manager = None
        state = None
        
        if force_by_name or not state_file.exists():
            # Force-by-name mode: look up resources by name
            console.print("[yellow]Force-by-name mode:[/yellow] Looking up resources by name...")
            
            with FabricClient(
                workspace_id=config.fabric.workspace_id,
                tenant_id=config.fabric.tenant_id,
            ) as client:
                # Find resources by name
                ont = client.find_ontology_by_name(config.resources.ontology.name)
                if ont:
                    ont_name = ont.get('displayName') or config.resources.ontology.name
                    resources_to_delete.append(('Ontology', ont_name, ont['id']))
                
                eh = client.find_eventhouse_by_name(config.resources.eventhouse.name)
                if eh:
                    eh_name = eh.get('displayName') or config.resources.eventhouse.name
                    resources_to_delete.append(('Eventhouse', eh_name, eh['id']))
                
                lh = client.find_lakehouse_by_name(config.resources.lakehouse.name)
                if lh:
                    lh_name = lh.get('displayName') or config.resources.lakehouse.name
                    resources_to_delete.append(('Lakehouse', lh_name, lh['id']))
        else:
            # Normal mode: use state file
            state_manager = SetupStateManager(demo_path, config.fabric.workspace_id, config.name)
            state = state_manager.load_state()
            
            if state is None:
                console.print("[yellow]Warning:[/yellow] Could not load state file.")
                console.print("Nothing to clean up.")
                return 0
            
            if state.ontology_id:
                resources_to_delete.append(('Ontology', state.ontology_name, state.ontology_id))
            if state.eventhouse_id:
                resources_to_delete.append(('Eventhouse', state.eventhouse_name, state.eventhouse_id))
            if state.lakehouse_id:
                resources_to_delete.append(('Lakehouse', state.lakehouse_name, state.lakehouse_id))

        if not resources_to_delete:
            console.print("[yellow]Warning:[/yellow] No resources found to delete.")
            if state_manager:
                state_manager.clear_state()
            return 0

        # Show what will be deleted
        console.print(Panel(f"Resources to clean up for demo: [bold red]{config.name}[/bold red]"))
        for resource_type, name, resource_id in resources_to_delete:
            console.print(f"  • {resource_type}: {name} ({resource_id})")
        console.print("")

        # Handle confirmation
        confirmed = getattr(args, 'confirm', False)
        if not confirmed:
            if global_config.confirm_cleanup:
                console.print("[yellow]This will permanently delete the resources listed above.[/yellow]")
                confirmed = Confirm.ask("Proceed with deletion?", default=False)
                if not confirmed:
                    console.print("[dim]Cancelled[/dim]")
                    return 0
            else:
                console.print("[yellow]Warning:[/yellow] This will delete the resources listed above.")
                console.print("Use --confirm or -y to proceed.")
                return 1

        # Perform deletion
        with FabricClient(
            workspace_id=config.fabric.workspace_id,
            tenant_id=config.fabric.tenant_id,
        ) as client:
            for resource_type, name, resource_id in resources_to_delete:
                console.print(f"Deleting {resource_type}: {name} ({resource_id})")
                try:
                    if resource_type == 'Ontology':
                        client.delete_ontology(resource_id)
                    elif resource_type == 'Eventhouse':
                        client.delete_eventhouse(resource_id)
                    elif resource_type == 'Lakehouse':
                        client.delete_lakehouse(resource_id)
                    console.print("[green]  ✓ Deleted[/green]")
                except Exception as e:
                    if "not found" in str(e).lower() or "404" in str(e):
                        console.print("[yellow]  ⚠ Already deleted or not found[/yellow]")
                    else:
                        raise

        # Mark state as cleaned up (if using state file)
        if state_manager:
            state_manager.mark_cleaned_up()
            console.print("\n[green]✓[/green] Cleanup completed - state file updated")
        else:
            console.print("\n[green]✓[/green] Cleanup completed")
        
        return 0

    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}")
        if getattr(args, 'debug', False) or logging.getLogger().level == logging.DEBUG:
            import traceback
            console.print(traceback.format_exc())
        return 1


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    # Handle debug mode
    debug = getattr(args, 'debug', False)
    setup_logging(args.verbose or debug)

    commands = {
        "config": run_config,
        "init": run_init,
        "validate": run_validate,
        "setup": run_setup,
        "run-step": run_step,
        "status": run_status,
        "list": run_list,
        "cleanup": run_cleanup,
        "docs": run_docs,
        "recover": run_recover,
    }

    handler = commands.get(args.command)
    if handler:
        try:
            return handler(args)
        except Exception as e:
            console.print(f"\n[red]Error:[/red] {e}")
            if debug:
                import traceback
                console.print(traceback.format_exc())
            return 1
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
