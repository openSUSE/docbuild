"""Build documentation products and deliverables."""

import click

from .cmd_dir import dir_cmd
from .cmd_index import index
from .cmd_run import run


@click.group(help=__doc__)
@click.pass_context
def build(ctx: click.Context) -> None:
    """Subcommand group for build operations.

    \f

    :param ctx: The Click context object.
    """  # noqa: D301
    pass  # pragma: no cover


# Add subcommands
build.add_command(dir_cmd)
build.add_command(index)
build.add_command(run)
