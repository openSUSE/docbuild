"""Manage repositories."""

import click

from .cmd_clone import clone
from .cmd_dir import cmd_dir
from .cmd_list import cmd_list


@click.group(help=__doc__)
@click.pass_context
def repo(ctx: click.Context) -> None:
    """Subcommand to repo management.

    :param ctx: The Click context object.
    """
    pass  # pragma: no cover


# Add subcommands
repo.add_command(clone)
repo.add_command(cmd_dir)
repo.add_command(cmd_list)
