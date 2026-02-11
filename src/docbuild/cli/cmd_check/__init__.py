import asyncio
from typing import TYPE_CHECKING

import click

from docbuild.cli.context import DocBuildContext

# Import Doctype for the type hint
from docbuild.models.doctype import Doctype

from ..callback import validate_doctypes
from .process import process_check_files


@click.group(name="check")
def cmd_check() -> None:
    """Check the environment or configuration for consistency."""
    pass


@cmd_check.command(name="files")
@click.argument("doctypes",
   nargs=-1,
   callback=validate_doctypes,
)
@click.pass_obj
def check_files(ctx: DocBuildContext, doctypes: tuple[Doctype, ...]) -> None:
    """Verify that DC files exist. Optional: specify 'product/version/lang'."""
    # Execute the logic via asyncio, passing the optional doctype filter
    # doctypes is a tuple of Doctype objects here
    missing: list[str] = asyncio.run(process_check_files(ctx, doctypes))

    if missing:
        missing_str = "\n- ".join(str(f) for f in missing if f)
        raise click.ClickException(
            f"DC file verification failed. The following files are missing:\n- {missing_str}"
        )
