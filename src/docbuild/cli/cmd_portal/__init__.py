"""Portal management commands for the docbuild CLI."""

import click

from docbuild.cli.cmd_portal.cmd_list import list_cmd


@click.group(name="portal")
def portal() -> None:
    """Manage and inspect the Portal configuration schema."""
    pass

portal.add_command(list_cmd)
