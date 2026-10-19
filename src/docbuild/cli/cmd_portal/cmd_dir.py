"""Display the portal configuration directory."""

import click

from docbuild.cli.console import console as stdout, console_err
from docbuild.cli.context import DocBuildContext


@click.command(name="dir")
@click.option(
    "--app",
    is_flag=True,
    help="Display the application config directory.",
)
@click.option(
    "--env",
    "env_flag",
    is_flag=True,
    help="Display the environment config directory (default).",
)
@click.pass_context
def dir_cmd(ctx: click.Context, app: bool, env_flag: bool) -> None:
    """Display the portal configuration directory.

    :param ctx: The Click context object.
    """
    context: DocBuildContext = ctx.obj

    if app and not env_flag:
        if not context.appconfig:
            console_err.print("[error]Application configuration is missing.[/]")
            ctx.exit(1)
        try:
            path = context.appconfig.paths.config_dir
        except AttributeError:
            console_err.print("[error]Application configuration does not define paths.config_dir.[/]")
            ctx.exit(1)
    else:
        if not context.envconfig:
            console_err.print("[error]Environment configuration is missing.[/]")
            ctx.exit(1)
        path = context.envconfig.paths.config_dir

    stdout.print(str(path))
