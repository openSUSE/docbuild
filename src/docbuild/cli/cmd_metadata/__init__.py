"""Extracts metadata from deliverables."""

import asyncio
import math

import click
from rich.console import Console

from ...models.doctype import Doctype
from ...utils.contextmgr import make_timer
from ..callback import validate_doctypes
from ..context import DocBuildContext
from .metaprocess import process

# Set up rich consoles for output
console_out = Console()


@click.command(help=__doc__)
@click.argument(
    'doctypes',
    nargs=-1,
    callback=validate_doctypes,
)
@click.pass_context
def metadata(
    ctx: click.Context,
    doctypes: tuple[Doctype],
) -> None:
    """Subcommand to create metadata files.

    :param ctx: The Click context object.
    """
    context: DocBuildContext = ctx.obj
    if context.envconfig is None:
        # log.critical('No envconfig found in context.')
        raise ValueError('No envconfig found in context.')

    timer = make_timer('metadata')
    result = 1  # Default exit code for interruption or error

    # The timer data object 't' will be populated by the context manager.
    # We define it here so it's accessible in the 'finally' block.
    t = None
    try:
        with timer() as t:
            result = asyncio.run(process(context, doctypes))
    finally:
        if t and not math.isnan(t.elapsed):
            console_out.print(f'Elapsed time {t.elapsed:0.2f}s')

    ctx.exit(result)
