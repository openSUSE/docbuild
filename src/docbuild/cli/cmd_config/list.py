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
@click.option("--validate", is_flag=True, help="Validate configuration before listing")
@click.pass_context
def list_config(ctx: click.Context, app: bool, env: bool, flat: bool, validate: bool) -> None:
    """List the configuration as JSON or flat text."""
    context = ctx.obj
    # If no specific flags are provided, show everything
    show_all = not (app or env)

    # We group the varying parameters into a list of configurations to process
    sections_to_check = [
        (
            app or show_all,
            context.appconfig,
            context.raw_appconfig,
            "Application Configuration",
            "app",
            "cyan",
        ),
        (
            env or show_all,
            context.envconfig,
            context.raw_envconfig,
            "Environment Configuration",
            "env",
            "yellow",
        ),
    ]

    for should_show, config, raw_config, title, key, color in sections_to_check:
        if not should_show:
            continue

        # Extract data if config exists, fallback to raw_config, or use empty dict
        data = config.model_dump(mode="json") if config else (raw_config or {})

        if data:
            print_section(title, data, key, flat, color)
