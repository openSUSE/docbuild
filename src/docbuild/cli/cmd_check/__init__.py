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
@click.pass_obj
def check_files(ctx: DocBuildContext, doctypes: tuple[Doctype, ...]) -> None:
    """Verify that DC files exist. Optional: specify 'product/version/lang'."""
    # Type guard: Ensure envconfig is loaded before accessing its attributes
    if ctx.envconfig is None:
        raise click.ClickException("Environment configuration is missing. Please initialize or check your config.")

    # Wrap the custom config types in pathlib.Path so Pylance knows expanduser() is valid
    main_portal_config = Path(ctx.envconfig.paths.main_portal_config).expanduser()
    repo_root = Path(ctx.envconfig.paths.repo_dir).expanduser()

    # Pass pure Python types to our isolated task logic
    missing: list[str] = asyncio.run(
        check_repository_files(main_portal_config, repo_root, doctypes)
    )

    if missing:
        missing_str = "\n- ".join(str(f) for f in missing if f)
        raise click.ClickException(
            f"DC file verification failed. The following files are missing:\n- {missing_str}"
        )
