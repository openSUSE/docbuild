import asyncio

import click

from docbuild.cli.context import DocBuildContext

from .process import process_check_files


@click.group(name="check")
def cmd_check() -> None:
    """Check the environment or configuration for consistency."""
    pass


@cmd_check.command(name="files")
# Add the optional argument as suggested by the reviewer
@click.argument("doctype", required=False)
@click.pass_obj
def check_files(ctx: DocBuildContext, doctype: str | None = None) -> None:
    """Verify that DC files exist. Optional: specify 'product/version/lang'."""
    # Execute the logic via asyncio, passing the optional doctype filter
    missing: list[str] = asyncio.run(process_check_files(ctx, doctype))

    if missing:
        missing_str = "\n- ".join(str(f) for f in missing if f)
        raise click.ClickException(
            f"DC file verification failed. The following files are missing:\n- {missing_str}"
        )
