"""CLI interface to manage and view configuration."""

import click

from .list import list_config
from .validate import validate


@click.group(name="config", help="Manage and view docbuild configuration.")
@click.pass_context
def config(ctx: click.Context) -> None:
    """Subcommand to manage the configuration files and their content."""
    pass


config.add_command(list_config)
config.add_command(validate)
