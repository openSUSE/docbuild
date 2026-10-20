"""Display the portal configuration directory."""

import click

from docbuild.cli.console import console as stdout
from docbuild.cli.context import DocBuildContext


@click.command(name="dir")
@click.pass_context
def dir_cmd(ctx: click.Context) -> None:
    """Display the portal configuration directory.

    Example:
        docbuild portal dir
    \f

    :param ctx: The Click context object.
    :returns: (None) Prints the resolved directory path to stdout.

    """  # noqa: D301 - Click requires an interpreted form-feed separator.
    context: DocBuildContext = ctx.obj
    assert context.envconfig is not None

    stdout.print(str(context.envconfig.paths.config_dir), soft_wrap=True)
