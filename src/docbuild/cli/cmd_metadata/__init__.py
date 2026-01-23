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
stdout = Console()
console_err = Console(stderr=True, style="red")


@click.command(help=__doc__)
@click.argument(
    "doctypes",
    nargs=-1,
    callback=validate_doctypes,
)
@click.option(
    "-E",
    "--exitfirst",
    is_flag=True,
    default=False,
    show_default=True,
    help="Exit on first failed deliverable.",
)
@click.option(
    "-S",
    "--skip-repo-update",
    is_flag=True,
    default=False,
    show_default=True,
    help="Skip updating git repositories before processing.",
)
@click.pass_context
def metadata(
    ctx: click.Context,
    doctypes: tuple[Doctype],
    exitfirst: bool,
    skip_repo_update: bool,
) -> None:
    """Subcommand to create metadata files.

    :param ctx: The Click context object.
    """
    context: DocBuildContext = ctx.obj
    timer = make_timer("metadata")
    result = 1  # Default exit code for interruption or error

    # The timer data object 't' will be populated by the context manager.
    # We define it here so it's accessible in the 'finally' block.
    t = None
    try:
        with timer() as t:
            result = asyncio.run(
                process(
                    context,
                    doctypes,
                    exitfirst=exitfirst,
                    skip_repo_update=skip_repo_update,
                )
            )
    finally:
        if t and not math.isnan(t.elapsed):
            stdout.print(f"Elapsed time {t.elapsed:0.2f}s")

    ctx.exit(result)
