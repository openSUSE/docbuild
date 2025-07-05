"""CLI interface to apply canonicals."""

import click

from .context import DocBuildContext


@click.command(help=__doc__)
@click.pass_context
def c14n(ctx: click.Context) -> None:
    """Subcommand to apply canonicals (canonicalization = c14n).

    :param ctx: The Click context object.
    """
    click.echo(f'[C17N] Verbosity: {ctx.obj.verbose}')
