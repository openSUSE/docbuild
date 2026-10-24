"""CLI interface to apply canonicals."""

import click


@click.command(name="c14n")
@click.pass_context
def c14n(ctx: click.Context) -> None:
    """CLI interface to apply canonicals (canonicalization = c14n).

    \f

    :param ctx: The Click context object.
    """  # noqa: D301
    # env = context.envconfig
    click.echo(f"[C17N] Verbosity: {ctx.obj.verbose}")
