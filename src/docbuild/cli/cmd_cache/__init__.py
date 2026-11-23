"""Manage docbuild caches."""

import itertools
from pathlib import Path

import click

from ...cli.alias import AliasGroup
from ...constants import CACHE_FILE_EXT
from ...models.doctype import Doctype
from ..callback import validate_doctypes
from ..completion import complete_doctypes
from ..console import console
from ..context import DocBuildContext
from ..message import OK, WARNING


def expand_meta_paths(meta_dir: Path, doctypes: tuple[Doctype]) -> list[Path]:
    """Expand doctypes into concrete metadata cache directory paths.

    The metadata cache is stored as ``<meta_dir>/<lang>/<product>/<docset>``.
    One path is built for each combination of product, docset, and language.
    Wildcards (``*``) are not expanded, so a doctype like ``sles/*/*`` does not
    match any directory.

    :param meta_dir: The metadata cache directory.
    :param doctypes: Doctypes to build the paths for.
    :return: The directory paths, for example ``<meta_dir>/en-us/sles/15-SP6``.
        If no doctypes are given, only ``meta_dir`` itself is returned.
    """
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


def expand_json_paths(json_dir: Path, doctypes: tuple[Doctype]) -> list[Path]:
    """Expand doctypes into concrete json cache directory paths.

    The JSON cache is stored as ``<json_dir>/<product>/<docset>.json``, so only
    the product of each doctype is used. Docsets and languages are ignored.

    :param json_dir: The JSON cache directory.
    :param doctypes: Doctypes to build the paths for.
    :return: One product directory for each doctype, for example
        ``<json_dir>/sles``.
        If no doctypes are given, only ``json_dir`` itself is returned.

    .. code-block:: pycon

        >>> doctype = Doctype.from_str("sles/15-SP6/en-us")
        >>> [str(p) for p in expand_json_paths(Path("/cache"), (doctype,))]
        ['/cache/sles']
    """
    if not doctypes:
        return [json_dir]

    paths = []
    for dt in doctypes:
        products = dt.product if isinstance(dt.product, list) else [dt.product]
        for prod in products:
            prod_name = str(getattr(prod, "acronym", prod))
            paths.append(json_dir / prod_name)
    return paths


def delete_cache_files(targets: list[Path], extension: str) -> int:
    """Delete cache files in the given target directories.

    Subdirectories are searched as well. Missing directories are skipped.

    :param targets: Directories to search.
    :param extension: Glob pattern of the files to delete, for example
        ``*.json``.
    :return: The number of deleted files.
    :raises OSError: If a file cannot be deleted.
    """
    deleted_count = 0
    for target in targets:
        for cache_file in target.rglob(extension):
            cache_file.unlink()
            deleted_count += 1
    return deleted_count


def print_cache_listing(directory: Path, title: str, target_paths: list[Path], extension: str) -> None:
    """Print cache files for a specific cache type.

    The files are sorted and shown relative to ``directory``. A warning is
    printed instead if ``directory`` does not exist or no files are found.

    :param directory: The cache directory to list.
    :param title: Heading of the listing, for example ``Meta Cache``.
    :param target_paths: Directories inside ``directory`` to search.
    :param extension: Glob pattern of the files to list, for example
        ``*.json``.
    """
    if not directory.exists():
        console.print(
            WARNING.render(console=console),
            f"{title} directory does not exist yet: {directory}",
        )
        return

    console.print(f"\n[header]{title}:[/] {directory}")
    cache_files: list[Path] = []
    for tp in target_paths:
        if tp.exists():
            cache_files.extend(tp.rglob(extension))

    if cache_files:
        for p in sorted(cache_files):
            console.print(f"- {p.relative_to(directory).as_posix()}")
    else:
        name = "meta" if "Meta" in title else "json"
        console.print(WARNING.render(console=console), f"No {name} cache files found.")


def gather_prune_targets(cache_type: str, doctypes: tuple[Doctype], meta_dir: Path, json_dir: Path) -> tuple[list[Path], list[Path]]:
    """Gather directories to prune for meta and json caches.

    Only directories that exist are returned.

    :param cache_type: Which cache to prune: ``meta``, ``json``, or ``all``.
    :param doctypes: Doctypes to limit the pruning to. If empty, the whole
        cache directory is used.
    :param meta_dir: The metadata cache directory.
    :param json_dir: The JSON cache directory.
    :return: The metadata directories and the JSON directories to prune.
    """
    targets_meta: list[Path] = []
    targets_json: list[Path] = []

    if cache_type in ("meta", "all") and meta_dir.exists():
        targets_meta = [tp for tp in expand_meta_paths(meta_dir, doctypes) if tp.exists()]

    if cache_type in ("json", "all") and json_dir.exists():
        targets_json = [tp for tp in expand_json_paths(json_dir, doctypes) if tp.exists()]

    return targets_meta, targets_json


def get_prune_confirmation_msg(cache_type: str, doctypes: tuple[Doctype]) -> str:
    """Format the confirmation message for pruning.

    :param cache_type: Which cache to prune: ``meta``, ``json``, or ``all``.
    :param doctypes: Doctypes that limit the pruning.
    :return: The question to ask before deleting the files.

    .. code-block:: pycon

        >>> get_prune_confirmation_msg("json", ())
        'Are you sure you want to delete ALL json cache files?'
    """
    target_str = "ALL cache files" if not doctypes else f"cache files for {len(doctypes)} doctype(s)"
    if cache_type != "all":
        target_str = f"ALL {cache_type} cache files" if not doctypes else f"{cache_type} cache files for {len(doctypes)} doctype(s)"
    return f"Are you sure you want to delete {target_str}?"


@click.group(cls=AliasGroup, help=__doc__)
def cache() -> None:
    """Subcommand group for cache management."""
    pass


@cache.command(name="dir")
@click.pass_context
def cache_dir(ctx: click.Context) -> None:
    """Display the path of the cache directories.

    \f

    :param ctx: The Click context that holds the environment config.
    """  # noqa: D301
    context: DocBuildContext = ctx.obj
    assert context.envconfig is not None

    paths = context.envconfig.paths

    console.print(f"[header]Base Cache Dir:[/] {paths.base_cache_dir}")
    console.print(f"[header]Meta Cache Dir:[/] {paths.meta_cache_dir}")
    console.print(f"[header]JSON Cache Dir:[/] {paths.json_cache_dir}")


@cache.command(name="list", aliases=["ls"])
@click.argument(
    "doctypes", nargs=-1, callback=validate_doctypes, shell_complete=complete_doctypes
)
@click.option("-t", "--type", "cache_type",
    type=click.Choice(["meta", "json", "all"]),
    default="all",
    help="Which cache type to list."
)
@click.pass_context
def cache_list(ctx: click.Context, doctypes: tuple[Doctype], cache_type: str) -> None:
    """List cache files.

    Optionally pass DOCTYPEs (e.g., sles/15-SP5/en-us) to filter the list.

    \f

    :param ctx: The Click context that holds the environment config.
    :param doctypes: Doctypes to filter the list. All files are listed if
        empty.
    :param cache_type: Which cache to list: ``meta``, ``json``, or ``all``.
    """  # noqa: D301
    context: DocBuildContext = ctx.obj
    assert context.envconfig is not None

    meta_dir = context.envconfig.paths.meta_cache_dir
    json_dir = context.envconfig.paths.json_cache_dir

    if cache_type in ("meta", "all"):
        print_cache_listing(
            meta_dir,
            "Meta Cache",
            expand_meta_paths(meta_dir, doctypes),
            f"*{CACHE_FILE_EXT}"
        )

    if cache_type in ("json", "all"):
        print_cache_listing(
            json_dir,
            "JSON Cache",
            expand_json_paths(json_dir, doctypes),
            "*.json"
        )


@cache.command(name="prune")
@click.argument(
    "doctypes", nargs=-1, callback=validate_doctypes, shell_complete=complete_doctypes
)
@click.option("-t", "--type", "cache_type", type=click.Choice(["meta", "json", "all"]), default="all", help="Which cache type to prune.")
@click.option("-y", "--yes", is_flag=True, help="Confirm deletion without prompting.")
@click.pass_context
def cache_prune(ctx: click.Context, doctypes: tuple[Doctype], cache_type: str, yes: bool) -> None:
    """Remove cache files.

    Removes all caches by default. Pass DOCTYPEs to remove specific caches.

    \f

    :param ctx: The Click context that holds the environment config.
    :param doctypes: Doctypes to limit the pruning to. For the JSON cache,
        only the product is used, so all docsets of that product are removed.
    :param cache_type: Which cache to prune: ``meta``, ``json``, or ``all``.
    :param yes: Skip the confirmation prompt.
    :raises click.Abort: If the user does not confirm.
    """  # noqa: D301
    context: DocBuildContext = ctx.obj
    assert context.envconfig is not None

    meta_dir = context.envconfig.paths.meta_cache_dir
    json_dir = context.envconfig.paths.json_cache_dir

    targets_meta, targets_json = gather_prune_targets(cache_type, doctypes, meta_dir, json_dir)

    if not targets_meta and not targets_json:
        console.print(WARNING.render(console=console), "No cache files found to prune.")
        return

    # Ask for confirmation
    if not yes:
        msg = get_prune_confirmation_msg(cache_type, doctypes)
        click.confirm(msg, abort=True)

    deleted_count = 0
    if targets_meta:
        deleted_count += delete_cache_files(targets_meta, f"*{CACHE_FILE_EXT}")
    if targets_json:
        deleted_count += delete_cache_files(targets_json, "*.json")

    console.print(
        OK.render(console=console), f"Successfully pruned {deleted_count} cache file(s)."
    )
