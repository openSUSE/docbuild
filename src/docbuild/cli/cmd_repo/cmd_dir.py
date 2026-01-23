"""Show the directory path for permanent repositories."""

import click

from ...cli.context import DocBuildContext


@click.command(help=__doc__, name="dir")
@click.pass_context
def cmd_dir(ctx: click.Context) -> None:
    """Show the directory path for permanent repositories.

    Outputs the path to the repository directory defined
    in the environment configuration.

    :param ctx: The Click context object.
    """
    context: DocBuildContext = ctx.obj
    if context.envconfig is None:
        raise ValueError("No envconfig found in context.")

    repo_dir = context.envconfig.get("paths", {}).get("repo_dir", None)
    print(repo_dir)
    ctx.exit(0)
