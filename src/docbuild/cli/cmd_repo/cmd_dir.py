"""Show the directory path for permanent repositories."""

from typing import cast

import click

from ...cli.context import DocBuildContext
from ...models.config.env import EnvConfig


@click.command(help=__doc__, name="dir")
@click.pass_context
def cmd_dir(ctx: click.Context) -> None:
    """Show the directory path for permanent repositories.

    Outputs the path to the repository directory defined
    in the environment configuration.

    :param ctx: The Click context object.
    """
    context: DocBuildContext = ctx.obj
    env = cast(EnvConfig, context.envconfig)
    repo_dir = env.paths.repo_dir
    print(repo_dir)
    ctx.exit(0)
