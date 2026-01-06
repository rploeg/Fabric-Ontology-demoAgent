"""Command-line interface for Fabric Demo Automation."""

import argparse
import sys
from pathlib import Path

from fabric_demo.loader import DemoLoader
from fabric_demo.runner import CleanupRunner, SetupRunner
from fabric_demo.state import StateManager


def cmd_setup(args: argparse.Namespace) -> int:
    """Handle 'setup' command."""
    runner = SetupRunner(args.demo_folder, args.workspace)
    success = runner.setup(force=args.force)
    return 0 if success else 1


def cmd_status(args: argparse.Namespace) -> int:
    """Handle 'status' command."""
    state = StateManager(args.demo_folder)
    print(f"\n📊 Status for: {args.demo_folder.name}")
    print("━" * 40)
    print(state.get_summary())
    return 0


def cmd_cleanup(args: argparse.Namespace) -> int:
    """Handle 'cleanup' command."""
    runner = CleanupRunner(args.demo_folder, args.workspace)
    success = runner.cleanup(confirm=not args.yes)
    return 0 if success else 1


def cmd_validate(args: argparse.Namespace) -> int:
    """Handle 'validate' command."""
    loader = DemoLoader(args.demo_folder)

    # Run validation
    errors = loader.validate()

    if errors:
        print(f"\n❌ Validation failed for: {args.demo_folder.name}")
        print("━" * 40)
        for error in errors:
            print(f"  • {error}")
        return 1

    # Load and show details
    try:
        demo = loader.load()
        print(f"\n✅ Demo package valid: {demo.name}")
        print("━" * 40)
        print(f"   Path: {demo.path}")
        print(f"   Lakehouse CSVs: {len(demo.lakehouse_csvs)}")
        for csv in demo.lakehouse_csvs:
            print(f"     • {csv.name}")
        print(f"   Eventhouse CSVs: {len(demo.eventhouse_csvs)}")
        for csv in demo.eventhouse_csvs:
            print(f"     • {csv.name}")
        print(f"   TTL file: {demo.ttl_file.name if demo.ttl_file else 'None'}")
        print(f"   Lakehouse bindings: {len(demo.lakehouse_bindings)}")
        for b in demo.lakehouse_bindings:
            print(f"     • {b['entityName']} → {b['table']}")
        print(f"   Eventhouse bindings: {len(demo.eventhouse_bindings)}")
        for b in demo.eventhouse_bindings:
            print(f"     • {b['entityName']} → {b['table']}")
        return 0
    except Exception as e:
        print(f"\n❌ Validation failed: {e}")
        return 1


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="fabric-demo",
        description="Fabric Ontology Demo Automation Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate demo package
  fabric-demo validate MedicalManufacturing/

  # Setup demo in Fabric workspace
  fabric-demo setup MedicalManufacturing/ --workspace abc123-def456-...

  # Check setup status
  fabric-demo status MedicalManufacturing/

  # Cleanup resources
  fabric-demo cleanup MedicalManufacturing/ --workspace abc123-def456-...
        """,
    )
    parser.add_argument(
        "--version", action="version", version="%(prog)s 1.0.0"
    )

    subparsers = parser.add_subparsers(dest="command", required=True, help="Command to run")

    # Setup command
    setup_parser = subparsers.add_parser(
        "setup",
        help="Set up demo in Fabric workspace",
        description="Creates Lakehouse, Eventhouse, and Ontology resources in Fabric",
    )
    setup_parser.add_argument(
        "demo_folder",
        type=Path,
        help="Path to demo folder (e.g., MedicalManufacturing/)",
    )
    setup_parser.add_argument(
        "--workspace",
        "-w",
        required=True,
        help="Fabric workspace ID (GUID)",
    )
    setup_parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force restart, ignoring previous state",
    )
    setup_parser.set_defaults(func=cmd_setup)

    # Status command
    status_parser = subparsers.add_parser(
        "status",
        help="Show setup status",
        description="Display current setup status and completed steps",
    )
    status_parser.add_argument(
        "demo_folder",
        type=Path,
        help="Path to demo folder",
    )
    status_parser.set_defaults(func=cmd_status)

    # Cleanup command
    cleanup_parser = subparsers.add_parser(
        "cleanup",
        help="Remove created resources",
        description="Delete all resources created by setup",
    )
    cleanup_parser.add_argument(
        "demo_folder",
        type=Path,
        help="Path to demo folder",
    )
    cleanup_parser.add_argument(
        "--workspace",
        "-w",
        required=True,
        help="Fabric workspace ID (GUID)",
    )
    cleanup_parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation prompt",
    )
    cleanup_parser.set_defaults(func=cmd_cleanup)

    # Validate command
    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate demo package structure",
        description="Check demo package structure without making API calls",
    )
    validate_parser.add_argument(
        "demo_folder",
        type=Path,
        help="Path to demo folder",
    )
    validate_parser.set_defaults(func=cmd_validate)

    # Parse and execute
    args = parser.parse_args()

    # Resolve demo folder path
    if hasattr(args, "demo_folder"):
        args.demo_folder = args.demo_folder.resolve()
        if not args.demo_folder.exists():
            print(f"❌ Error: Demo folder not found: {args.demo_folder}")
            sys.exit(1)

    # Run command
    exit_code = args.func(args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
