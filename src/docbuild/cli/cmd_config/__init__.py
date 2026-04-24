"""CLI interface for docbuild configuration management."""

import click

from .list import list_config
from .validate import validate_config


@click.group(
    name="config",
    help="CLI interface to manage and verify configuration files.",
)
@click.pass_context
def config(ctx: click.Context) -> None:
    """Subcommand to manage docbuild configuration (TOML and XML)."""
    pass


# Register the task-oriented subcommands
config.add_command(list_config)
config.add_command(validate_config)
