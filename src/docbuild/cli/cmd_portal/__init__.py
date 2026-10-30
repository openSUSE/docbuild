"""Manage Portal XML configuration."""

import logging

import click

from ..alias import AliasGroup
from .cmd_dir import dir_cmd
from .cmd_list import list_cmd
from .cmd_validate import validate

log = logging.getLogger(__name__)


@click.group(name="portal", cls=AliasGroup, help=__doc__)
@click.pass_context
def portal(ctx: click.Context) -> None:
    """Manage Portal XML configuration.

    \f

    :param ctx: The Click context object.
    """  # noqa: D301
    pass  # pragma: no cover


# Register subcommands
portal.add_command(list_cmd, aliases=["ls"])
portal.add_command(validate)
portal.add_command(dir_cmd)
