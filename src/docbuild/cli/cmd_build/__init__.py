"""Build documentation products and deliverables."""

import click

from .cmd_run import run


@click.group(help=__doc__)
@click.pass_context
def build(ctx: click.Context) -> None:
    """Subcommand group for build operations.

    :param ctx: The Click context object.
    """
    pass  # pragma: no cover


# Add subcommands
build.add_command(run)