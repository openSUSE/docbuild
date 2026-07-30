"""Extracts metadata from deliverables."""

import asyncio
import math
from pathlib import Path

import click
from rich.console import Console

from docbuild.cli.callback import validate_doctypes
from docbuild.cli.context import DocBuildContext
from docbuild.models.doctype import Doctype
from docbuild.tasks.metadata import generate_metadata
from docbuild.utils.contextmgr import make_timer

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

    # 1. Protect against Pylance's Optional[EnvConfig] warning
    if not context.envconfig:
        console_err.print("Environment configuration is missing.")
        ctx.exit(1)

    timer = make_timer("metadata")
    result = 1  # Default exit code for interruption or error

    # 2. Unpack and cast all custom Pydantic directory types to standard Paths
    env = context.envconfig
    main_portal_config = Path(env.paths.main_portal_config)
    tmp_metadata_dir = Path(env.paths.tmp.tmp_metadata_dir)
    repo_dir = Path(env.paths.repo_dir)
    tmp_repo_dir = Path(env.paths.tmp_repo_dir)
    meta_cache_dir = Path(env.paths.meta_cache_dir)
    dapsmetatmpl = str(env.build.daps.meta)

    stdout.print(f"Config path: {env.paths.config_dir}")

    t = None
    try:
        with timer() as t:
            result = asyncio.run(
                generate_metadata(
                    main_portal_config=main_portal_config,
                    tmp_metadata_dir=tmp_metadata_dir,
                    repo_dir=repo_dir,
                    tmp_repo_dir=tmp_repo_dir,
                    meta_cache_dir=meta_cache_dir,
                    dapsmetatmpl=dapsmetatmpl,
                    doctypes=doctypes,
                    exitfirst=exitfirst,
                    skip_repo_update=skip_repo_update,
                )
            )
    finally:
        if t and not math.isnan(t.elapsed):
            stdout.print(f"Elapsed time {t.elapsed:0.2f}s")

    ctx.exit(result)
