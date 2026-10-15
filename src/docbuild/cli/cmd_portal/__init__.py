"""Manage Portal XML configuration."""

import logging

import click

from docbuild.cli.alias import AliasGroup
from docbuild.cli.cmd_portal.cmd_list import list_cmd

from .cmd_validate import validate

log = logging.getLogger(__name__)


@click.group(cls=AliasGroup, help=__doc__)
@click.pass_context
def portal(ctx: click.Context) -> None:
    """Subcommand to Portal XML management.

    :param ctx: The Click context object.
    """
    pass  # pragma: no cover


# Register both subcommands
portal.add_command(list_cmd, aliases=["ls"])
portal.add_command(validate)
