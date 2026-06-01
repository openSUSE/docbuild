"""Portal management commands for the docbuild CLI."""

import asyncio
from collections import defaultdict

import click
from lxml import etree  # type: ignore
from rich.console import Console
from rich.tree import Tree

from docbuild.cli.cmd_portal.process import parse_portal_config
from docbuild.cli.context import DocBuildContext
from docbuild.config.xml.list import list_all_deliverables
from docbuild.models.deliverable import Deliverable
from docbuild.models.doctype import Doctype


def build_hierarchy(
    deliverables: list[Deliverable],
) -> tuple[dict, dict]:
    """Group Deliverables into a hierarchy and build a translation index.

    :param deliverables: A list of Deliverable models to organize.
    :return: A tuple of (hierarchy_dict, translation_index_dict).
    """
    hierarchy: dict[str, dict[str, dict[str, list[Deliverable]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )
    # Maps: product -> docset -> deliverable_id -> set of languages
    translation_index: dict[str, dict[str, dict[str, set[str]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(set))
    )

    for deliv in deliverables:
        lang = str(deliv.xml.lang)
        product = deliv.xml.productid or "unknown-product"
        docset = deliv.xml.docsetid or "unknown-docset"

        # Determine base ID
        d_id = deliv.xml.node.get("id", "unnamed-deliverable")

        hierarchy[lang][product][docset].append(deliv)

        # Dynamically discover all translations for this deliverable by peeking at the XML tree
        if deliv.xml.docset_node is not None:
            # Find all locales in this docset that have a deliverable with the same ID
            for loc in deliv.xml.docset_node.xpath(f"resources/locale[deliverable[@id='{d_id}']]"):
                if loc_lang := loc.get("lang"):
                    translation_index[product][docset][d_id].add(loc_lang)
        else:
            translation_index[product][docset][d_id].add(lang)

    return hierarchy, translation_index


def _parse_doctypes(doctypes: tuple[str, ...], console: Console) -> list[Doctype] | None:
    """Parse raw CLI arguments into Doctype objects with default fallbacks."""
    if not doctypes:
        return None

    parsed_doctypes = []
    for dt in doctypes:
        # Toms' Suggestion: Fallback to default English language if omitted
        slash_count = dt.count("/")
        if slash_count == 1:
            dt = f"{dt}/en-us"
        elif slash_count == 0:
            dt = f"{dt}/*/en-us"

        try:
            parsed_doctypes.append(Doctype.from_str(dt))
        except ValueError as e:
            console.print(f"[red]Error parsing doctype:[/red] {e}")
            raise click.Abort() from e

    return parsed_doctypes


def _get_display_name(deliv: Deliverable, d_id: str) -> str:
    """Determine the main display name for a deliverable."""
    if deliv.xml.is_prebuilt:
        title_node = deliv.xml.node.find("title")
        title = title_node.text if title_node is not None else d_id
        return f"{title} (Prebuilt)"

    dc_file = deliv.xml.dcfile
    return f"{d_id} ({dc_file})" if dc_file else d_id


def _append_translations(
    deliv_branch: Tree,
    translation_index: dict[str, dict[str, dict[str, set[str]]]],
    product: str,
    docset: str,
    d_id: str,
    lang: str
) -> None:
    """Append translation metadata to the deliverable branch."""
    all_langs = translation_index.get(product, {}).get(docset, {}).get(d_id, set())
    other_langs = sorted(other_lang for other_lang in all_langs if other_lang != lang)
    if other_langs:
        deliv_branch.add(f"Translations: {', '.join(other_langs)}")


def _append_formats(deliv_branch: Tree, deliv: Deliverable) -> None:
    """Append output formats metadata to the deliverable branch."""
    if attrs := deliv.xml.format_attrs():
        fmt_names = {"pdf": "PDF", "html": "HTML", "single-html": "Single-HTML", "epub": "EPUB"}
        available = [fmt_names.get(k, k.upper()) for k, v in attrs.items() if v]
        if available:
            deliv_branch.add(f"Formats: {', '.join(available)}")


def _append_categories(deliv_branch: Tree, deliv: Deliverable) -> None:
    """Append category metadata to the deliverable branch."""
    if cat := deliv.xml.node.get("category"):
        deliv_branch.add(f"Category: {cat.replace('-', ' ').capitalize()}")


def _append_repo(deliv_branch: Tree, deliv: Deliverable, repo_format: str) -> None:
    """Append repository metadata to the deliverable branch."""
    if repo := deliv.xml.git_remote():
        # Safely extract long URL or fallback to short string representation
        repo_val = getattr(repo, "url", getattr(repo, "clone_url", str(repo))) if repo_format == "long" else str(repo)
        deliv_branch.add(f"Repo: {repo_val}")


def _build_deliverable_branch(
    docset_branch: Tree,
    deliv: Deliverable,
    lang: str,
    product: str,
    docset: str,
    translation_index: dict[str, dict[str, dict[str, set[str]]]],
    show_trans: bool,
    show_formats: bool,
    show_categories: bool,
    repo_format: str | None,
) -> None:
    """Format and append a single deliverable node to the Rich Tree."""
    d_id = deliv.xml.node.get("id", "unnamed-deliverable")

    # 1. Format the main display name
    display_name = _get_display_name(deliv, d_id)
    deliv_branch = docset_branch.add(display_name)

    # 2. Automatically show URLs for prebuilt deliverables
    if deliv.xml.is_prebuilt:
        for url_node in deliv.xml.node.xpath("prebuilt/url"):
            if href := url_node.get("href"):
                deliv_branch.add(f"URL: [link={href}]{href}[/link]")

    # 3. Add Optional Metadata based on CLI Flags
    if show_trans:
        _append_translations(deliv_branch, translation_index, product, docset, d_id, lang)
    if show_formats:
        _append_formats(deliv_branch, deliv)
    if show_categories:
        _append_categories(deliv_branch, deliv)
    if repo_format:
        _append_repo(deliv_branch, deliv, repo_format)


def _print_hierarchy(
    hierarchy: dict[str, dict[str, dict[str, list[Deliverable]]]],
    translation_index: dict[str, dict[str, dict[str, set[str]]]],
    console: Console,
    show_trans: bool,
    show_formats: bool,
    show_categories: bool,
    repo_format: str | None,
) -> None:
    """Render and print the nested hierarchy as a Rich Tree."""
    for lang, products in sorted(hierarchy.items()):
        root_tree = Tree(f"[bold blue]{lang}/[/bold blue]")

        for product, docsets in sorted(products.items()):
            prod_branch = root_tree.add(f"[bold]{product}[/bold]")

            for docset, delivs in sorted(docsets.items()):
                docset_branch = prod_branch.add(f"[cyan]{docset}[/cyan]")

                # Sort deliverables by ID for stable output
                for deliv in sorted(delivs, key=lambda d: d.xml.node.get("id", "")):
                    _build_deliverable_branch(
                        docset_branch,
                        deliv,
                        lang,
                        product,
                        docset,
                        translation_index,
                        show_trans,
                        show_formats,
                        show_categories,
                        repo_format,
                    )

        console.print(root_tree)
        console.print()


async def async_list_cmd(
    ctx: DocBuildContext,
    doctypes: tuple[str, ...],
    console: Console,
    show_trans: bool,
    show_formats: bool,
    show_categories: bool,
    repo_format: str | None,
) -> None:
    """Async worker to fetch the XML, parse Doctypes, and build the tree."""
    parsed_doctypes = _parse_doctypes(doctypes, console)

    # 2. Get XML Tree
    # The application framework guarantees envconfig is loaded before command execution.
    # We use assert to satisfy the type checker without redundant runtime error handling.
    assert ctx.envconfig is not None

    # We rely on the Pydantic env model to handle existence and path validations natively
    portal_xml_path = ctx.envconfig.paths.main_portal_config.expanduser()

    try:
        tree = await parse_portal_config(portal_xml_path)
    except (OSError, etree.XMLSyntaxError, etree.XIncludeError) as e:
        console.print(f"[red]Error loading XML schema:[/red] {e}")
        raise click.Abort() from e

    # 3. Fetch and wrap Deliverables into Domain Objects
    # Consuming the generator directly saves memory over converting to an intermediate list
    deliverables = [
        Deliverable(_node=node)
        for node in list_all_deliverables(tree, parsed_doctypes)
    ]

    if not deliverables:
        console.print("[yellow]No deliverables found matching the criteria.[/yellow]")
        return

    hierarchy, translation_index = build_hierarchy(deliverables)

    _print_hierarchy(
        hierarchy,
        translation_index,
        console,
        show_trans,
        show_formats,
        show_categories,
        repo_format
    )


@click.command(name="list")
@click.option("--trans", "-T", is_flag=True, help="List available translations.")
@click.option("--formats", "-F", is_flag=True, help="List available output formats.")
@click.option("--categories", "-C", is_flag=True, help="List categories.")
@click.option(
    "--repo",
    "-R",
    type=click.Choice(["short", "long"]),
    is_flag=False,
    flag_value="short",
    default=None,
    help="List repository origin (defaults to short if no type provided)."
)
@click.argument("doctypes", nargs=-1)
@click.pass_obj
def list_cmd(
    ctx: DocBuildContext,
    doctypes: tuple[str, ...],
    trans: bool,
    formats: bool,
    categories: bool,
    repo: str | None,
) -> None:
    r"""List products, docsets, and deliverables from the portal config.

    Accepts optional DOCTYPE arguments to filter the output.
    Format: [PRODUCT]/[DOCSETS]@[LIFECYCLES]/[LANGS]

    Example:
        docbuild portal list sles/15-SP6

    \f

    :param ctx: The DocBuildContext passed from the CLI, containing config and options.
    :param doctypes: A tuple of doctype strings passed as arguments to the command.
    :param trans: Show translation metadata.
    :param formats: Show output formats metadata.
    :param categories: Show categories metadata.
    :param repo: Show repository metadata (short or long).

    """
    console = Console()
    asyncio.run(async_list_cmd(ctx, doctypes, console, trans, formats, categories, repo))
