"""Clone repositories.

Pass any of the following URLs to clone:

\b
* HTTPS URLs like ``https://github.com/org/repo.git``
* SSH URLS like git@github.com:org/repo.git
* Abbreviated URLs like 'org/repo'

Use ``--all`` to clone every repository from the portal configuration.
"""  # noqa: D301

import asyncio
import logging

import click

from ...cli.context import DocBuildContext
from ...constants import GITLOGGER_NAME
from ...tasks.repo import clone_repositories

log = logging.getLogger(__name__)

git_logger = logging.getLogger(GITLOGGER_NAME)


@click.command(help=__doc__)
@click.argument(
    "repos",
    nargs=-1,
)
@click.option(
    "--all",
    "all_repos",
    is_flag=True,
    help="Clone all repositories from the portal configuration.",
)
@click.pass_context
def clone(ctx: click.Context, repos: tuple[str, ...], all_repos: bool) -> None:
    """Clone repositories into permanent directory.

    :param repos: A tuple of repository selectors.
    :param all_repos: Clone all repositories instead of a selection.
    :param ctx: The Click context object.
    :raises click.UsageError: If neither or both of repos and ``--all`` are given.
    """
    if repos and all_repos:
        raise click.UsageError("Pass either repositories or --all, not both.")
    if not repos and not all_repos:
        raise click.UsageError(
            "Pass one or more repositories, or --all to clone them all."
        )

    context: DocBuildContext = ctx.obj

    # Type guard: Ensure envconfig is loaded before accessing its attributes
    if context.envconfig is None:
        raise click.ClickException("Environment configuration is missing.")

    main_portal_config = context.envconfig.paths.main_portal_config
    repo_dir = context.envconfig.paths.repo_dir

    async def main() -> int:
        return await asyncio.create_task(
            clone_repositories(main_portal_config, repo_dir, repos), name="repo-clone"
        )

    result = asyncio.run(main())
    log.info(f"Clone process completed with exit code: {result}")
    ctx.exit(result)
