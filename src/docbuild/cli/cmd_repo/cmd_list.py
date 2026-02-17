"""List the available permanent repositories."""

from pathlib import Path

import click
from rich.console import Console

from ...cli.context import DocBuildContext

console = Console()
console_err = Console(stderr=True)


@click.command(help=__doc__, name="list")
@click.pass_context
def cmd_list(ctx: click.Context) -> None:
    """List the available permanent repositories.

    Outputs the directory names of all repositories defined in the
    environment configuration.
    If no repositories are defined, it outputs a message indicating that
    no repositories are available.

    :param ctx: The Click context object.
    """
    context: DocBuildContext = ctx.obj
    env = context.envconfig

    repo_dir = env.paths.repo_dir
    repo_dir = Path(repo_dir).resolve()
    if not repo_dir.exists():
        console_err.print(
            f"[red]ERROR:[/] No permanent repositories found in {repo_dir}.",
        )
        ctx.exit(1)

    console.print(f"Available permanent repositories in {repo_dir}:")
    for path in Path(repo_dir).iterdir():
        if path.is_dir() and not path.name.startswith("."):
            console.print(f"  - {path}")

    ctx.exit(0)
