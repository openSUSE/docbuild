"""Show the directory path for permanent repositories."""


import click

from ...cli.context import DocBuildContext


@click.command(name="dir")
@click.pass_context
def cmd_dir(ctx: click.Context) -> None:
    """Show the directory path for permanent repositories.

    Outputs the path to the repository directory defined
    in the environment configuration.

    \f

    :param ctx: The Click context object.
    """  # noqa: D301
    context: DocBuildContext = ctx.obj
    env = context.envconfig
    repo_dir = env.paths.repo_dir
    print(repo_dir)
    ctx.exit(0)
