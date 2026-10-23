"""CLI command to show the build target directory."""

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ...cli.cmd_cli import DocBuildContext


@click.command(name="dir")
@click.pass_context
def dir_cmd(ctx: click.Context) -> None:
    """Print the directory where build data is stored."""
    context: DocBuildContext = ctx.obj
    assert context.envconfig is not None

    click.echo(context.envconfig.paths.target.target_base_dir)
