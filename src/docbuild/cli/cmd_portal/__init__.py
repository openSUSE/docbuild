"""Manage Portal XML configuration."""

import logging

import click

from docbuild.cli.cmd_portal.cmd_list import list_cmd

from .cmd_validate import validate

log = logging.getLogger(__name__)


@click.group(name="portal")
@click.pass_context
def portal(ctx: click.Context) -> None:
    """Manage Portal XML configuration.

    \f

    :param ctx: The Click context object.
    """  # noqa: D301
    pass  # pragma: no cover


# Register both subcommands
portal.add_command(list_cmd)
portal.add_command(validate)
