"""CLI interface to list the configuration."""

from typing import Any

import click
from rich import print_json
from rich.console import Console

from ...utils.flatten import flatten_dict

console = Console()


def print_section(title: str, data: dict[str, Any], prefix: str, flat: bool, color: str) -> None:
    """Print the Application and Environment configuration sections.

    :param title: The title of the section to print.
    :param data: The configuration data to print (as a dictionary).
    :param prefix: The prefix to use for flat keys (e.g., "app" or "env").
    :param flat: Whether to print in flat format or as JSON.
    :param color: The color to use for the keys in flat format.
    """
    if flat:
        # Use the generator directly to avoid holding a full list in memory
        for k, v in flatten_dict(data, prefix):
            console.print(f"[bold {color}]{k}[/bold {color}] = [green]{v}[/green]")
    else:
        console.print(f"\n# {title}", style="blue")
        print_json(data=data)


def print_portal(doctypes: list[Any], flat: bool) -> None:
    """Print the Portal and Doctype metadata section.

    :param doctypes: The list of doctype metadata objects to print.
    :param flat: Whether to print in flat format or as a structured list.
    """
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
    """List the configuration as JSON or flat text.

    :param ctx: The Click context object containing the loaded configuration.
    :param app: Whether to show only application configuration.
    :param env: Whether to show only environment configuration.
    :param portal: Whether to show only portal/doctype metadata.
    :param flat: Whether to output in flat dotted format instead of JSON.
    """
    context = ctx.obj
    show_all = not (app or env or portal)

    if (app or show_all) and context.appconfig:
        app_data = context.appconfig.model_dump(mode="json")
        print_section("Application Configuration", app_data, "app", flat, "cyan")

    if (env or show_all) and context.envconfig:
        env_data = context.envconfig.model_dump(mode="json")
        print_section("Environment Configuration", env_data, "env", flat, "yellow")

    if (portal or show_all) and context.doctypes:
        print_portal(context.doctypes, flat)
