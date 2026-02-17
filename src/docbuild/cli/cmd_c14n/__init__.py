"""CLI interface to apply canonicals."""

import click


@click.command(help=__doc__)
@click.pass_context
def c14n(ctx: click.Context) -> None:
    """Subcommand to apply canonicals (canonicalization = c14n).

    :param ctx: The Click context object.
    """
    # env = context.envconfig
    click.echo(f"[C17N] Verbosity: {ctx.obj.verbose}")
