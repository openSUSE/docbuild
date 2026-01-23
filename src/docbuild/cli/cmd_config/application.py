"""CLI interface to show the configuration of the application files."""

import click
from rich import print  # noqa: A004
from rich.pretty import Pretty


@click.command(
    help=__doc__,
)
@click.pass_context
def app(ctx: click.Context) -> None:
    """Subcommand to show the application's configuration.

    :param ctx: The Click context object.
    """
    if ctx.obj.appconfigfiles:
        files = ", ".join(str(f) for f in ctx.obj.appconfigfiles)
        click.secho(f"# Application config files '{files}'", fg="blue")
        print(Pretty(ctx.obj.appconfig, expand_all=True))
    else:
        click.secho("# No application config files provided", fg="yellow")
        print(Pretty(ctx.obj.appconfig, expand_all=True))
