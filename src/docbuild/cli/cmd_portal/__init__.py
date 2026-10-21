"""Manage Portal XML configuration."""

import logging

import click

from docbuild.cli.cmd_portal.cmd_list import list_cmd

from .cmd_dir import dir_cmd
from .cmd_validate import validate

log = logging.getLogger(__name__)


@click.group(help=__doc__)
@click.pass_context
def portal(ctx: click.Context) -> None:
    """Subcommand to Portal XML management.

    :param ctx: The Click context object.
    """
    pass  # pragma: no cover


# Register subcommands
portal.add_command(list_cmd)
portal.add_command(validate)
portal.add_command(dir_cmd)
