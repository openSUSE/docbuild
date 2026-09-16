"""Manage docbuild caches."""

import itertools
from pathlib import Path

import click
from rich.console import Console

from docbuild.cli.callback import validate_doctypes
from docbuild.cli.context import DocBuildContext
from docbuild.constants import CACHE_FILE_EXT
from docbuild.models.doctype import Doctype

stdout = Console()


def _expand_meta_paths(meta_dir: Path, doctypes: tuple[Doctype]) -> list[Path]:
    """Expand doctypes into concrete metadata cache directory paths."""
    if not doctypes:
        return [meta_dir]

    paths = []
    for dt in doctypes:
        products = dt.product if isinstance(dt.product, list) else [dt.product]
        docsets = dt.docset if isinstance(dt.docset, list) else [dt.docset]

        for prod, docset, lang in itertools.product(products, docsets, dt.langs):
            # Safely get attributes to satisfy Pylance strict typing
            prod_name = str(getattr(prod, "acronym", prod))
            lang_name = str(getattr(lang, "language", lang))
            paths.append(meta_dir / lang_name / prod_name / str(docset))
    return paths


def _expand_json_paths(json_dir: Path, doctypes: tuple[Doctype]) -> list[Path]:
    """Expand doctypes into concrete json cache directory paths."""
    if not doctypes:
        return [json_dir]

    paths = []
    for dt in doctypes:
        products = dt.product if isinstance(dt.product, list) else [dt.product]
        for prod in products:
            prod_name = str(getattr(prod, "acronym", prod))
            paths.append(json_dir / prod_name)
    return paths


def _delete_cache_files(targets: list[Path], extension: str) -> int:
    """Delete cache files in the given target directories."""
    deleted_count = 0
    for target in targets:
        for cache_file in target.rglob(extension):
            cache_file.unlink()
            deleted_count += 1
    return deleted_count


def _print_cache_listing(directory: Path, title: str, color: str, target_paths: list[Path], extension: str) -> None:
    """Print cache files for a specific cache type."""
    if not directory.exists():
        stdout.print(f"[yellow]{title} directory does not exist yet: {directory}[/yellow]")
        return

    stdout.print(f"\n[bold {color}]{title}:[/bold {color}] {directory}")
    cache_files: list[Path] = []
    for tp in target_paths:
        if tp.exists():
            cache_files.extend(tp.rglob(extension))

    if cache_files:
        for p in sorted(cache_files):
            stdout.print(f"- {p.relative_to(directory).as_posix()}")
    else:
        name = "meta" if "Meta" in title else "json"
        stdout.print(f"[yellow]No {name} cache files found.[/yellow]")


def _gather_prune_targets(cache_type: str, doctypes: tuple[Doctype], meta_dir: Path, json_dir: Path) -> tuple[list[Path], list[Path]]:
    """Gather directories to prune for meta and json caches."""
    targets_meta: list[Path] = []
    targets_json: list[Path] = []

    if cache_type in ("meta", "all") and meta_dir.exists():
        targets_meta = [tp for tp in _expand_meta_paths(meta_dir, doctypes) if tp.exists()]

    if cache_type in ("json", "all") and json_dir.exists():
        targets_json = [tp for tp in _expand_json_paths(json_dir, doctypes) if tp.exists()]

    return targets_meta, targets_json


def _get_prune_confirmation_msg(cache_type: str, doctypes: tuple[Doctype]) -> str:
    """Format the confirmation message for pruning."""
    target_str = "ALL cache files" if not doctypes else f"cache files for {len(doctypes)} doctype(s)"
    if cache_type != "all":
        target_str = f"ALL {cache_type} cache files" if not doctypes else f"{cache_type} cache files for {len(doctypes)} doctype(s)"
    return f"Are you sure you want to delete {target_str}?"


@click.group(help=__doc__)
def cache() -> None:
    """Subcommand group for cache management."""
    pass


@cache.command(name="dir")
@click.pass_context
def cache_dir(ctx: click.Context) -> None:
    """Display the path of the cache directories."""
    context: DocBuildContext = ctx.obj
    assert context.envconfig is not None

    paths = context.envconfig.paths

    stdout.print(f"[bold]Base Cache Dir:[/bold] {paths.base_cache_dir}")
    stdout.print(f"[bold]Meta Cache Dir:[/bold] {paths.meta_cache_dir}")
    stdout.print(f"[bold]JSON Cache Dir:[/bold] {paths.json_cache_dir}")


@cache.command(name="list")
@click.argument("doctypes", nargs=-1, callback=validate_doctypes)
@click.option("-t", "--type", "cache_type",
    type=click.Choice(["meta", "json", "all"]),
    default="all",
    help="Which cache type to list."
)
@click.pass_context
def cache_list(ctx: click.Context, doctypes: tuple[Doctype], cache_type: str) -> None:
    """List cache files.

    Optionally pass DOCTYPEs (e.g., sles/15-SP5/en-us) to filter the list.
    """
    context: DocBuildContext = ctx.obj
    assert context.envconfig is not None

    meta_dir = context.envconfig.paths.meta_cache_dir
    json_dir = context.envconfig.paths.json_cache_dir

    if cache_type in ("meta", "all"):
        _print_cache_listing(
            meta_dir,
            "Meta Cache",
            "blue",
            _expand_meta_paths(meta_dir, doctypes),
            f"*{CACHE_FILE_EXT}"
        )

    if cache_type in ("json", "all"):
        _print_cache_listing(
            json_dir,
            "JSON Cache",
            "green",
            _expand_json_paths(json_dir, doctypes),
            "*.json"
        )


@cache.command(name="prune")
@click.argument("doctypes", nargs=-1, callback=validate_doctypes)
@click.option("-t", "--type", "cache_type", type=click.Choice(["meta", "json", "all"]), default="all", help="Which cache type to prune.")
@click.option("-y", "--yes", is_flag=True, help="Confirm deletion without prompting.")
@click.pass_context
def cache_prune(ctx: click.Context, doctypes: tuple[Doctype], cache_type: str, yes: bool) -> None:
    """Remove cache files.

    Removes all caches by default. Pass DOCTYPEs to remove specific caches.
    """
    context: DocBuildContext = ctx.obj
    assert context.envconfig is not None

    meta_dir = context.envconfig.paths.meta_cache_dir
    json_dir = context.envconfig.paths.json_cache_dir

    targets_meta, targets_json = _gather_prune_targets(cache_type, doctypes, meta_dir, json_dir)

    if not targets_meta and not targets_json:
        stdout.print("[yellow]No cache files found to prune.[/yellow]")
        return

    # Ask for confirmation
    if not yes:
        msg = _get_prune_confirmation_msg(cache_type, doctypes)
        click.confirm(msg, abort=True)

    deleted_count = 0
    if targets_meta:
        deleted_count += _delete_cache_files(targets_meta, f"*{CACHE_FILE_EXT}")
    if targets_json:
        deleted_count += _delete_cache_files(targets_json, "*.json")

    stdout.print(f"[bold green]Successfully pruned {deleted_count} cache file(s).[/bold green]")
