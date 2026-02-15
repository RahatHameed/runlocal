#!/usr/bin/env python3
"""CLI entry point for running scripts."""

import argparse
import sys

from rich.console import Console
from rich.table import Table

from scripts import SCRIPTS


console = Console()


def list_scripts():
    """Print available scripts in a table."""
    table = Table(title="Available Scripts")
    table.add_column("Name", style="cyan")
    table.add_column("Description", style="green")
    table.add_column("Version", style="dim")

    for name, script_class in SCRIPTS.items():
        table.add_row(
            name,
            script_class.config.description,
            script_class.config.version
        )

    console.print(table)


def run_script(script_name: str, verbose: bool = False, **kwargs):
    """Run the specified script."""
    if script_name not in SCRIPTS:
        console.print(f"[red]Error: Unknown script '{script_name}'[/red]")
        console.print()
        list_scripts()
        sys.exit(1)

    script_class = SCRIPTS[script_name]
    script = script_class()

    console.print(f"[bold cyan]Running: {script.config.name}[/bold cyan]")
    console.print(f"[dim]{script.config.description}[/dim]")
    console.print()

    result = script.run(verbose=verbose, **kwargs)

    # Print final result summary
    console.print()
    if result.success:
        console.print(f"[bold green]Result: {result.message}[/bold green]")
    else:
        console.print(f"[bold red]Result: {result.message}[/bold red]")
        for error in result.errors:
            console.print(f"[red]  - {error}[/red]")

    return 0 if result.success else 1


def main():
    parser = argparse.ArgumentParser(
        description="Run local automation scripts (no API required)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all available scripts
  python run.py --list

  # Read files in current directory (summary)
  python run.py file-reader --path . --pattern "*.py"

  # Read files with full content
  python run.py file-reader --path . --pattern "*.txt" --verbose

  # Trigger GitHub workflow (summary)
  python run.py workflow-dispatch --project test

  # Trigger with full logs
  python run.py workflow-dispatch --project test --verbose

  # Trigger with custom parameters
  python run.py workflow-dispatch --project test --param message="Hello!"
""",
    )

    # Global arguments
    parser.add_argument(
        "script",
        nargs="?",
        choices=list(SCRIPTS.keys()),
        help="Script to run",
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List available scripts",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed output (full file contents, full logs)",
    )

    # File reader arguments
    parser.add_argument(
        "--path",
        default=".",
        help="Directory path for file-reader (default: current directory)",
    )
    parser.add_argument(
        "--pattern",
        default="*",
        help="File pattern for file-reader (default: *)",
    )

    # Workflow dispatch arguments
    parser.add_argument(
        "--project",
        help="Project name from projects.yaml (for workflow-dispatch)",
    )
    parser.add_argument(
        "--workflow",
        help="Override workflow file name",
    )
    parser.add_argument(
        "--branch",
        help="Override branch name",
    )
    parser.add_argument(
        "--param",
        action="append",
        dest="params",
        metavar="KEY=VALUE",
        help="Workflow parameter (can be repeated)",
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Don't wait for workflow completion (workflow-dispatch only)",
    )

    args = parser.parse_args()

    # Handle --list
    if args.list:
        list_scripts()
        return 0

    # Require a script name
    if not args.script:
        console.print("[yellow]No script specified. Use --list to see available scripts.[/yellow]")
        console.print()
        list_scripts()
        return 1

    # Build kwargs based on script type
    kwargs = {}

    if args.script == "file-reader":
        kwargs["path"] = args.path
        kwargs["pattern"] = args.pattern

    elif args.script == "workflow-dispatch":
        if not args.project:
            console.print("[red]Error: --project is required for workflow-dispatch[/red]")
            console.print("[dim]Example: python run.py workflow-dispatch --project test[/dim]")
            return 1

        kwargs["project"] = args.project
        kwargs["wait"] = not args.no_wait

        if args.workflow:
            kwargs["workflow"] = args.workflow
        if args.branch:
            kwargs["branch"] = args.branch
        if args.params:
            kwargs["params"] = args.params

    elif args.script == "workflow-status":
        if not args.project:
            console.print("[red]Error: --project is required for workflow-status[/red]")
            console.print("[dim]Example: python run.py workflow-status --project test[/dim]")
            return 1

        kwargs["project"] = args.project
        if args.workflow:
            kwargs["workflow"] = args.workflow

    return run_script(args.script, verbose=args.verbose, **kwargs)


if __name__ == "__main__":
    sys.exit(main())
