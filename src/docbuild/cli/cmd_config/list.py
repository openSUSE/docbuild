"""CLI interface to list the configuration."""

from typing import Any

import click
from rich import print_json
from rich.console import Console

from ...utils.flatten import flatten_dict

console = Console()

def print_section(title: str, data: dict[str, Any], prefix: str, flat: bool, color: str) -> None:
    """Print a configuration section in either flat or JSON format."""
    if flat:
        for k, v in flatten_dict(data, prefix):
            # Using repr(v) ensures strings are quoted and types like Paths are clear
            console.print(f"[bold {color}]{k}[/bold {color}] = [green]{v!r}[/green]")
    else:
        console.print(f"\n# {title}", style="blue")
        print_json(data=data)


@click.command(name="list")
@click.option("--app", is_flag=True, help="Show only application configuration")
@click.option("--env", is_flag=True, help="Show only environment configuration")
@click.option("--flat", is_flag=True, help="Output in flat dotted format (git-style)")
@click.pass_context
def list_config(ctx: click.Context, app: bool, env: bool, flat: bool) -> None:
    """List the configuration as JSON or flat text."""
    context = ctx.obj
    # If no specific flags are provided, show everything
    show_all = not (app or env)

    if (app or show_all) and context.appconfig:
        # mode="json" handles IPv4Address, Path, and Enums automatically
        app_data = context.appconfig.model_dump(mode="json")
        print_section("Application Configuration", app_data, "app", flat, "cyan")

    if (env or show_all) and context.envconfig:
        # Handles serialization for environment settings
        env_data = context.envconfig.model_dump(mode="json")
        print_section("Environment Configuration", env_data, "env", flat, "yellow")
