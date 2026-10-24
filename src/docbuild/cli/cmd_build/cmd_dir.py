"""CLI command to show the build target directory."""

from typing import TYPE_CHECKING

import click

from ...cli.console import console

if TYPE_CHECKING:
    from ...cli.cmd_cli import DocBuildContext


@click.command(name="dir")
@click.pass_context
def dir_cmd(ctx: click.Context) -> None:
    """Print the directory where build data is stored.

    This command outputs the raw path to the target base directory,
    making it ideal for use in scripts.
    """
    context: DocBuildContext = ctx.obj
    assert context.envconfig is not None

    console.print(context.envconfig.paths.target.target_base_dir)
