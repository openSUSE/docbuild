import asyncio
from collections import Counter
from pathlib import Path

import click
from rich.markup import escape
from rich.tree import Tree

from docbuild.cli.context import DocBuildContext
from docbuild.constants import STATUS_ICONS
from docbuild.models.doctype import Doctype
from docbuild.tasks.check import check_repository_files

from ..callback import validate_doctypes
from ..console import console


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
    main_portal_config = ctx.envconfig.paths.main_portal_config
    repo_root = ctx.envconfig.paths.repo_dir
    prebuilt_dir = ctx.envconfig.paths.prebuilt_dir

    # Pass pure Python types to our isolated task logic
    async def main() -> list[tuple[str, str, str, str]]:
        return await asyncio.create_task(
            check_repository_files(
                main_portal_config, repo_root, doctypes, prebuilt_dir
            ),
            name="check-files",
        )

    results = asyncio.run(main())
    counts = Counter(status for *_, status in results)
    print_results(results)
    print_summary(counts)

    if counts["missing"]:
        raise click.ClickException(
            f"DC file verification failed: {counts['missing']} file(s) missing."
        )


def print_results(results: list[tuple[str, str, str, str]]) -> None:
    """Print the results as a tree grouped by product/docset/lang."""
    grouped: dict[str, list[tuple[str, str, str]]] = {}
    for identifier, dcfile, repo_surl, status in results:
        grouped.setdefault(identifier, []).append((dcfile, repo_surl, status))

    for identifier, entries in grouped.items():
        head, lang = identifier.rsplit("/", 1)
        product, docset = head.split("/", 1)
        tree = Tree(f"[product]{product}[/]/[docset]{docset}[/]/[lang]{lang}[/]")
        for dcfile, repo_surl, status in entries:
            suffix = (
                f" [repo]{escape(f'[{repo_surl}]')}[/]"
                if status == "missing"
                else ""
            )
            tree.add(f"{STATUS_ICONS[status]} {dcfile}{suffix}")
        console.print(tree)


def print_summary(counts: Counter[str]) -> None:
    """Print how many files were found, skipped, and missing."""
    files = counts["found"]
    errors = counts["missing"]
    console.print(
        f"\nFound {files} {'file' if files == 1 else 'files'}, "
        f"{counts['skipped']} skipped, "
        f"{errors} {'error' if errors == 1 else 'errors'}."
    )
