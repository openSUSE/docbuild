"""Manage docbuild caches."""

import itertools
from pathlib import Path

import click
from rich.console import Console
from rich.tree import Tree

from docbuild.cli.callback import validate_doctypes
from docbuild.cli.context import DocBuildContext
from docbuild.models.doctype import Doctype

stdout = Console()
console_err = Console(stderr=True, style="red")


def _expand_doctype_paths(meta_dir: Path, doctypes: tuple[Doctype]) -> list[Path]:
    """Expand doctypes into concrete directory paths."""
    if not doctypes:
        return [meta_dir]

    paths = []
    for dt in doctypes:
        products = dt.product if isinstance(dt.product, list) else [dt.product]
        docsets = dt.docset if isinstance(dt.docset, list) else [dt.docset]
        langs = getattr(dt, "langs", getattr(dt, "lang", []))
        if isinstance(langs, str):
            langs = [langs]

        for prod, docset, lang in itertools.product(products, docsets, langs):
            paths.append(meta_dir / str(prod) / str(docset) / str(lang))
    return paths


def _delete_cache_files(targets: list[Path]) -> int:
    """Delete cache files in the given target directories."""
    deleted_count = 0
    for target in targets:
        for cache_file in target.rglob("*.cache"):
            cache_file.unlink()
            deleted_count += 1
    return deleted_count


@click.group(help=__doc__)
def cache() -> None:
    """Subcommand group for cache management."""
    pass


@cache.command(name="dir")
@click.pass_context
def cache_dir(ctx: click.Context) -> None:
    """Display the path of the cache directories."""
    context: DocBuildContext = ctx.obj

    if not context.envconfig:
        console_err.print("Environment configuration is missing.")
        ctx.exit(1)

    paths = context.envconfig.paths

    stdout.print(f"[bold]Base Cache Dir:[/bold] {paths.base_cache_dir}")
    stdout.print(f"[bold]Meta Cache Dir:[/bold] {paths.meta_cache_dir}")
    stdout.print(f"[bold]JSON Cache Dir:[/bold] {paths.json_cache_dir}")


@cache.command(name="list")
@click.argument("doctypes", nargs=-1, callback=validate_doctypes)
@click.pass_context
def cache_list(ctx: click.Context, doctypes: tuple[Doctype]) -> None:
    """List cache files in a tree structure.

    Optionally pass DOCTYPEs (e.g., sles/15-SP5/en-us) to filter the list.
    """
    context: DocBuildContext = ctx.obj

    if not context.envconfig:
        console_err.print("Environment configuration is missing.")
        ctx.exit(1)

    meta_dir = context.envconfig.paths.meta_cache_dir

    if not meta_dir.exists():
        stdout.print(f"[yellow]Cache directory does not exist yet: {meta_dir}[/yellow]")
        return

    # Gather cache files based on doctypes
    cache_files: list[Path] = []
    target_paths = _expand_doctype_paths(meta_dir, doctypes)
    for tp in target_paths:
        if tp.exists():
            cache_files.extend(tp.rglob("*.cache"))

    if not cache_files:
        stdout.print("[yellow]No cache files found.[/yellow]")
        return

    # Build the Rich Tree
    tree = Tree(f":file_folder: [bold blue]Meta Cache:[/bold blue] {meta_dir}")
    nodes: dict[Path, Tree] = {meta_dir: tree}

    for p in sorted(cache_files):
        # Ensure parent folder nodes exist in the tree
        parents = list(p.relative_to(meta_dir).parents)[::-1]
        for parent in parents:
            if parent.name == "":  # Skip the '.' root
                continue
            dir_path = meta_dir / parent
            if dir_path not in nodes:
                nodes[dir_path] = nodes[dir_path.parent].add(f":file_folder: [bold cyan]{parent.name}[/bold cyan]")

        # Add the file to its direct parent node
        nodes[p.parent].add(f":page_facing_up: [green]{p.name}[/green]")

    stdout.print(tree)


@cache.command(name="prune")
@click.argument("doctypes", nargs=-1, callback=validate_doctypes)
@click.option("-y", "--yes", is_flag=True, help="Confirm deletion without prompting.")
@click.pass_context
def cache_prune(ctx: click.Context, doctypes: tuple[Doctype], yes: bool) -> None:
    """Remove cache files.

    Removes all caches by default. Pass DOCTYPEs to remove specific caches.
    """
    context: DocBuildContext = ctx.obj

    if not context.envconfig:
        console_err.print("Environment configuration is missing.")
        ctx.exit(1)

    meta_dir = context.envconfig.paths.meta_cache_dir

    if not meta_dir.exists():
        stdout.print("[yellow]Cache is already empty.[/yellow]")
        return

    # Determine what to delete
    targets: list[Path] = []
    target_paths = _expand_doctype_paths(meta_dir, doctypes)
    for tp in target_paths:
        if tp.exists():
            targets.append(tp)
        elif doctypes:
            try:
                rel_path = tp.relative_to(meta_dir)
                stdout.print(f"[yellow]No cache found to prune for {rel_path}[/yellow]")
            except ValueError:
                stdout.print(f"[yellow]No cache found to prune for {tp}[/yellow]")

    if not targets:
        return

    # Ask for confirmation
    if not yes:
        target_str = "ALL cache files" if not doctypes else f"cache files for {len(doctypes)} doctype(s)"
        click.confirm(f"Are you sure you want to delete {target_str}?", abort=True)

    # Delete the files
    deleted_count = _delete_cache_files(targets)

    stdout.print(f"[bold green]Successfully pruned {deleted_count} cache file(s).[/bold green]")
