"""Publish documentation deliverables to a remote destination."""

import click

from .cmd_run import run


@click.group(help=__doc__)
@click.pass_context
def publish(ctx: click.Context) -> None:
    """Subcommand group for publish operations.

    \f

    :param ctx: The Click context object.
    """  # noqa: D301
    pass  # pragma: no cover


# Add subcommands
publish.add_command(run)
