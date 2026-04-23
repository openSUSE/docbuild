"""CLI interface to list the configuration."""

from typing import Any

import click
from rich import print_json
from rich.console import Console

console = Console()

def flatten_dict(d: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    """Flatten a nested dictionary into dotted keys (e.g., app.logging.level)."""
    items: list[tuple[str, Any]] = []
    for k, v in d.items():
        new_key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key).items())
        else:
            items.append((new_key, v))
    return dict(items)

def _print_section(title: str, data: dict[str, Any], prefix: str, flat: bool, color: str) -> None:
    """Print the Application and Environment configuration sections."""
    if flat:
        for k, v in flatten_dict(data, prefix).items():
            console.print(f"[bold {color}]{k}[/bold {color}] = [green]{v}[/green]")
    else:
        console.print(f"\n# {title}", style="blue")
        print_json(data=data)

def _print_portal(doctypes: list[Any], flat: bool) -> None:
    """Print the Portal and Doctype metadata section."""
    if not flat:
        console.print("\n# Portal/Doctype Metadata", style="blue")

    for doctype in doctypes:
        name = getattr(doctype, "name", "Unknown")
        path = str(getattr(doctype, "path", "N/A"))
        if flat:
            console.print(f"[bold magenta]portal.{name}[/bold magenta] = [green]{path}[/green]")
        else:
            console.print(f"  - [bold]{name}[/bold]: {path}")

@click.command(name="list")
@click.option("--app", is_flag=True, help="Show only application configuration")
@click.option("--env", is_flag=True, help="Show only environment configuration")
@click.option("--portal", is_flag=True, help="Show only portal/doctype metadata")
@click.option("--flat", is_flag=True, help="Output in flat dotted format (git-style)")
@click.pass_context
def list_config(ctx: click.Context, app: bool, env: bool, portal: bool, flat: bool) -> None:
    """List the configuration as JSON or flat text."""
    context = ctx.obj
    show_all = not (app or env or portal)

    if (app or show_all) and context.appconfig:
        _print_section("Application Configuration", context.appconfig.model_dump(), "app", flat, "cyan")

    if (env or show_all) and context.envconfig:
        _print_section("Environment Configuration", context.envconfig.model_dump(), "env", flat, "yellow")

    if (portal or show_all) and context.doctypes:
        _print_portal(context.doctypes, flat)
