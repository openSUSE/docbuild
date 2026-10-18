import asyncio
from pathlib import Path

import click

from docbuild.cli.context import DocBuildContext
from docbuild.models.doctype import Doctype
from docbuild.tasks.check import check_repository_files

from ..callback import validate_doctypes


@click.group(name="check")
def cmd_check() -> None:
    """Check the environment or configuration for consistency."""
    pass


@cmd_check.command(name="files")
@click.argument(
    "doctypes",
    nargs=-1,
    callback=validate_doctypes,
)
@click.option(
    "--all",
    "check_all",
    is_flag=True,
    default=False,
    help="Check all DC files (all products, docsets, and languages).",
)
@click.pass_obj
def check_files(
    ctx: DocBuildContext,
    doctypes: tuple[Doctype, ...],
    check_all: bool,
) -> None:
    """Verify that DC files exist.

    Provide one or more doctypes in 'product/version/lang' format, or use
    ``--all`` to check every DC file. The two ways are mutually exclusive.
    """
    if check_all and doctypes:
        raise click.UsageError(
            "The --all option cannot be combined with doctypes. "
            "Use either --all or one or more doctypes."
        )

    if not check_all and not doctypes:
        raise click.UsageError(
            "Please specify one or more doctypes, or use --all to check every DC file."
        )

    # Type guard: Ensure envconfig is loaded before accessing its attributes
    if ctx.envconfig is None:
        raise click.ClickException("Environment configuration is missing. Please initialize or check your config.")

    # Wrap the custom config types in pathlib.Path so Pylance knows expanduser() is valid
    main_portal_config = ctx.envconfig.paths.main_portal_config
    repo_root = ctx.envconfig.paths.repo_dir

    # Pass pure Python types to our isolated task logic.
    # An empty doctype list represents the "--all" case (use the task defaults).
    selected = list(doctypes) if doctypes else None

    async def main() -> list[str]:
        return await asyncio.create_task(
            check_repository_files(main_portal_config, repo_root, selected),
            name="check-files",
        )

    missing: list[str] = asyncio.run(main())

    if missing:
        missing_str = "\n- ".join(str(f) for f in missing if f)
        raise click.ClickException(
            f"DC file verification failed. The following files are missing:\n- {missing_str}"
        )
