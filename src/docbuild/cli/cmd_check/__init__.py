import asyncio
from pathlib import Path
import sys

import click
from rich.tree import Tree

from ...models.doctype import Doctype
from ...tasks.check import check_repository_files
from ..callback import validate_doctypes
from ..completion import complete_doctypes
from ..console import console
from ..context import DocBuildContext


@click.group(name="check")
def cmd_check() -> None:
    """Check the environment or configuration for consistency."""
    pass


@cmd_check.command(name="files")
@click.argument(
    "doctypes",
    nargs=-1,
    callback=validate_doctypes,
    shell_complete=complete_doctypes,
)
@click.option(
    "--all",
    "check_all",
    is_flag=True,
    default=False,
    help="Check all DC files (all products, docsets, and languages).",
)
@click.pass_obj
def check_files(  # noqa: C901
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
    prebuilt_dir = ctx.envconfig.paths.prebuilt_dir

    # Pass pure Python types to our isolated task logic.
    # An empty doctype list represents the "--all" case (use the task defaults).
    selected = list(doctypes) if doctypes else None

    async def main() -> dict:
        return await asyncio.create_task(
            check_repository_files(main_portal_config, repo_root, prebuilt_dir, selected),
            name="check-files",
        )

    results = asyncio.run(main())

    total_found = 0
    total_skipped = 0
    total_errors = 0
    total_xrefs = 0

    # Build the Rich UI output
    for doctype_str, files in results.items():
        if not files:
            continue

        tree = Tree(f"[bold]{doctype_str}[/bold]")
        for f in files:
            if f.status == "found":
                tree.add(f"{f.dcfile} [success]✓ OK[/]")
                total_found += 1
            elif f.status == "skipped":
                tree.add(f"{f.dcfile} [skipped]⏭️ (Skipped)[/]")
                total_skipped += 1
            elif f.status == "xref":
                tree.add(f"{f.dcfile} [xref]🔗 (xref)[/]")
                total_xrefs += 1
            else:
                tree.add(f"{f.dcfile} [error]🔴[/]")
                total_errors += 1

        console.print(tree)

    xref_str = f", {total_xrefs} xrefs" if total_xrefs > 0 else ""
    console.print(f"\nFound {total_found} files, {total_skipped} skipped{xref_str}, {total_errors} error.")

    if total_errors > 0:
        sys.exit(1)
