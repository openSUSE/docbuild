"""Manage Portal XML configuration."""

import asyncio
from collections.abc import Iterator
import logging
from pathlib import Path

import click

from ..context import DocBuildContext
from . import process as process_mod
from .cmd_validate import validate

log = logging.getLogger(__name__)


@click.group(help=__doc__)
@click.pass_context
def portal(ctx: click.Context) -> None:
    """Subcommand to Portal XML management.

    :param ctx: The Click context object.
    """
    pass  # pragma: no cover


portal.add_command(validate)
