"""Clone repositories.

Pass any of the following URLs to clone:

\b
* HTTPS URLs like ``https://github.com/org/repo.git``
* SSH URLS like git@github.com:org/repo.git
* Abbreviated URLs like 'org/repo'
"""  # noqa: D301

import asyncio
import logging
from pathlib import Path

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
@click.pass_context
def clone(ctx: click.Context, repos: tuple[str, ...]) -> None:
    """Clone repositories into permanent directory.

    :param repos: A tuple of repository selectors. If empty, all repos are cloned.
    :param ctx: The Click context object.
    """
    context: DocBuildContext = ctx.obj

    # Type guard: Ensure envconfig is loaded before accessing its attributes
    if context.envconfig is None:
        raise click.ClickException("Environment configuration is missing.")

    main_portal_config = Path(context.envconfig.paths.main_portal_config).expanduser()
    repo_dir = Path(context.envconfig.paths.repo_dir).expanduser()

    result = asyncio.run(clone_repositories(main_portal_config, repo_dir, repos))
    log.info(f"Clone process completed with exit code: {result}")
    ctx.exit(result)
