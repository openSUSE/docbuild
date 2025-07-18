"""Clone repositories.

Pass any of the following URLs to clone:

\b
* HTTPS URLs like ``https://github.com/org/repo.git``
* SSH URLS like git@github.com:org/repo.git
* Abbreviated URLs like 'org/repo'
"""  # noqa: D301

import asyncio
import logging

import click

from ...cli.context import DocBuildContext
from ...logging import GITLOGGERNAME
from .process import process

log = logging.getLogger(GITLOGGERNAME)


@click.command(help=__doc__)
@click.argument(
    'repos',
    nargs=-1,
)
@click.pass_context
def clone(ctx: click.Context, repos: tuple[str, ...]) -> None:
    """Clone repositories into permanent directory.

    :param repos: A tuple of repository selectors. If empty, all repos are cloned.
    :param ctx: The Click context object.
    """
    context: DocBuildContext = ctx.obj
    if context.envconfig is None:
        raise ValueError('No envconfig found in context.')

    result = asyncio.run(process(context, repos))
    log.info(f'Clone process completed with exit code: {result}')
    ctx.exit(result)
