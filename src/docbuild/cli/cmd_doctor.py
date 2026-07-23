"""CLI command to check system dependencies."""

import click
from rich.console import Console
from rich.table import Table

from ..utils.sysdeps import check_dependencies


@click.command(name="doctor", help="Check system dependencies required by docbuild.")
def doctor() -> None:
    """Check system dependencies and display their status."""
    console = Console()
    results = check_dependencies()

    table = Table(
        title="docbuild System Dependencies",
        show_header=True,
        header_style="bold magenta"
    )
    table.add_column("Tool", style="cyan", no_wrap=True)
    table.add_column("Required", style="blue")
    table.add_column("Found", style="green")
    table.add_column("Status", justify="left")

    has_errors = False

    for res in results:
        name = res["name"]
        required = res["required"] or "Any"
        found = res["found"] or "---"

        if not res["is_installed"]:
            status = "[red]✗ Missing[/red]"
            has_errors = True
            found = "[dim]---[/dim]"
        elif not res["is_valid"]:
            status = f"[red]✗ {res['message']}[/red]"
            has_errors = True
            found = f"[red]{found}[/red]"
        elif "Warning" in res["message"]:
            status = f"[yellow]⚠ {res['message']}[/yellow]"
        else:
            status = "[green]✓ OK[/green]"

        table.add_row(name, required, found, status)

    console.print()
    console.print(table)

    if has_errors:
        console.print("\n[red]Some required system dependencies are missing or outdated.[/red]")
        console.print("Please install them using your system package manager (e.g., zypper, apt, or brew).")
        # Exit with error code 1 so CI systems fail if this is run as a pre-flight check
        click.get_current_context().exit(1)
    else:
        console.print("\n[green]All system dependencies look good![/green]")
