"""Portal management commands for the docbuild CLI."""

import asyncio
from collections import defaultdict
from dataclasses import dataclass

import click
from lxml import etree  # type: ignore
from rich.console import Console
from rich.tree import Tree

from ...cli.context import DocBuildContext
from ...config.xml.list import list_all_deliverables
from ...models.deliverable import Deliverable
from ...models.doctype import Doctype
from ...models.product import Product
from ...tasks.portal import parse_portal_config


@dataclass
class DisplayDeliverable:
    """Wrapper for a Deliverable to project its inherited translations."""

    model: Deliverable
    lang: str
    is_inherited: bool


def build_hierarchy(
    deliverables: list[DisplayDeliverable],
) -> dict[str, dict[str, dict[str, list[DisplayDeliverable]]]]:
    """Group Deliverables into a hierarchy.

    :param deliverables: A list of DisplayDeliverable models to organize.
    :return: A hierarchy_dict mapping lang -> product -> docset -> deliverables.
    """
    hierarchy: dict[str, dict[str, dict[str, list[DisplayDeliverable]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )

    for dd in deliverables:
        lang = dd.lang
        product = dd.model.xml.product_id or "unknown-product"
        docset = dd.model.xml.docset_path or "unknown-docset"

        hierarchy[lang][product][docset].append(dd)

    return hierarchy


def parse_doctypes(doctypes: tuple[str, ...], console: Console) -> list[Doctype] | None:
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


def get_display_name(dd: DisplayDeliverable, d_id: str) -> str:
    """Determine the main display name for a deliverable."""
    if dd.model.xml.is_prebuilt:
        title_node = dd.model.xml.node.find("title")
        title = title_node.text if title_node is not None else d_id
        base = f"{title} (Prebuilt)"
    else:
        dc_file = dd.model.xml.dcfile
        base = f"{d_id} ({dc_file})" if dc_file else d_id

    if dd.is_inherited:
        return f"{base} [en-us blueprint]"
    return base


def append_translations(deliv_branch: Tree, deliv: Deliverable, lang: str) -> None:
    """Append translation metadata to the deliverable branch."""
    other_langs = sorted(other_lang for other_lang in deliv.xml.translations if other_lang != lang)
    if other_langs:
        deliv_branch.add(f"Translations: {', '.join(other_langs)}")


def append_formats(deliv_branch: Tree, deliv: Deliverable) -> None:
    """Append output formats metadata to the deliverable branch."""
    if attrs := deliv.xml.format_attrs():
        fmt_names = {"pdf": "PDF", "html": "HTML", "single-html": "Single-HTML", "epub": "EPUB"}
        available = [fmt_names.get(k, k.upper()) for k, v in attrs.items() if v]
        if available:
            deliv_branch.add(f"Formats: {', '.join(available)}")


def append_categories(deliv_branch: Tree, deliv: Deliverable) -> None:
    """Append category metadata to the deliverable branch."""
    if cat_title := deliv.xml.category_title:
        deliv_branch.add(f"Category: {cat_title}")


def append_repo(deliv_branch: Tree, deliv: Deliverable, repo_format: str) -> None:
    """Append repository metadata to the deliverable branch."""
    repo = deliv.xml.git_remote()
    if repo:
        if isinstance(repo, str):
            repo_val = repo
        else:
            # Using surl for the short variant, url/clone_url for long
            repo_val = getattr(repo, "url", getattr(repo, "clone_url", str(repo))) if repo_format == "long" else getattr(repo, "surl", str(repo))
        deliv_branch.add(f"Repo: {repo_val}")


def build_deliverable_branch(
    docset_branch: Tree,
    dd: DisplayDeliverable,
    show_trans: bool,
    show_formats: bool,
    show_categories: bool,
    repo_format: str | None,
) -> None:
    """Format and append a single deliverable node to the Rich Tree."""
    deliv = dd.model
    d_id = deliv.xml.deliverableid or "unnamed-deliverable"

    # 1. Format the main display name
    display_name = get_display_name(dd, d_id)
    deliv_branch = docset_branch.add(display_name)

    # 2a. Automatically show URLs for prebuilt deliverables
    if deliv.xml.is_prebuilt:
        for url_node in deliv.xml.node.xpath("prebuilt/url"):
            if href := url_node.get("href"):
                deliv_branch.add(f"URL: [link={href}]{href}[/link]")

    # 3. Add Optional Metadata based on CLI Flags
    if show_trans:
        append_translations(deliv_branch, deliv, dd.lang)
    if show_formats:
        append_formats(deliv_branch, deliv)
    if show_categories:
        append_categories(deliv_branch, deliv)
    if repo_format:
        append_repo(deliv_branch, deliv, repo_format)


def print_hierarchy(
    hierarchy: dict[str, dict[str, dict[str, list[DisplayDeliverable]]]],
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
                for dd in sorted(delivs, key=lambda d: d.model.xml.node.get("id", "")):
                    build_deliverable_branch(
                        docset_branch,
                        dd,
                        show_trans,
                        show_formats,
                        show_categories,
                        repo_format,
                    )

        console.print(root_tree)
        console.print()


def print_flat(
    deliverables: list[DisplayDeliverable],
    console: Console,
    show_trans: bool,
    show_formats: bool,
    show_categories: bool,
    repo_format: str | None,
) -> None:
    """Render and print the deliverables as a flat list."""
    # Sort logically: lang -> product -> docset -> id
    sorted_deliverables = sorted(
        deliverables,
        key=lambda dd: (
            dd.lang,
            dd.model.xml.product_id or "",
            dd.model.xml.docset_path or "",
            dd.model.xml.node.get("id", ""),
        )
    )

    for dd in sorted_deliverables:
        deliv = dd.model
        lang = dd.lang
        product = deliv.xml.product_id or "unknown-product"
        docset = deliv.xml.docset_path or "unknown-docset"
        d_id = deliv.xml.deliverableid or "unnamed-deliverable"

        display_name = get_display_name(dd, d_id)

        # Build the flat root string with colors matching the hierarchy
        flat_title = f"[bold blue]{lang}[/bold blue]/[bold]{product}[/bold]/[cyan]{docset}[/cyan]:{display_name}"
        deliv_tree = Tree(flat_title)

        # Attach metadata if requested
        if deliv.xml.is_prebuilt:
            for url_node in deliv.xml.node.xpath("prebuilt/url"):
                if href := url_node.get("href"):
                    deliv_tree.add(f"URL: [link={href}]{href}[/link]")

        if show_trans:
            append_translations(deliv_tree, deliv, lang)
        if show_formats:
            append_formats(deliv_tree, deliv)
        if show_categories:
            append_categories(deliv_tree, deliv)
        if repo_format:
            append_repo(deliv_tree, deliv, repo_format)

        # Print cleanly if there's no metadata branches, otherwise print the tree block
        if deliv_tree.children:
            console.print(deliv_tree)
        else:
            console.print(flat_title)


def validate_docsets_against_xml(
    doctypes: list[Doctype], tree: etree._ElementTree | etree._Element, console: Console
) -> None:
    """Dynamically validate that provided docsets exist for their respective products."""
    errors = []

    for dt in doctypes:
        if dt.product and dt.product != Product.ALL and dt.docset and "*" not in dt.docset:
            prod_val = dt.product.acronym

            # Use the class's own string parser to bypass strict __init__ type-checking issues
            broad_dt = Doctype.from_str(f"{prod_val}/*/*")

            # Harvest all valid docset IDs using the Deliverable abstraction
            valid_docsets = set()
            for node in list_all_deliverables(tree, [broad_dt]):
                deli = Deliverable(_node=node)
                if deli.xml.docset_path:
                    valid_docsets.add(deli.xml.docset_path)

            valid_docsets_str = ["*", *sorted(valid_docsets)]

            for ds in dt.docset:
                if ds not in valid_docsets:
                    allowed_str = ", ".join(f"'{v}'" for v in valid_docsets_str)
                    errors.append(f"* {prod_val}/{ds} is not a valid Docset.\n  Allowed values are: {allowed_str}")

    if errors:
        err_count = len(errors)
        noun = "error" if err_count == 1 else "errors"
        console.print(f"[red]Error parsing doctype:[/red] {err_count} validation {noun} for Doctype:\n")
        for err in errors:
            console.print(err)
        raise click.Abort()


def _matches_query(dd: DisplayDeliverable, doctypes: tuple[str, ...]) -> bool:
    """Check if a deliverable matches any of the provided doctype queries."""
    prod = dd.model.xml.product_id or ""
    doc = dd.model.xml.docset_path or ""
    lang = dd.lang

    for q in doctypes:
        parts = q.split("/")
        q_prod = parts[0]
        q_doc = parts[1] if len(parts) > 1 else "*"
        q_lang = parts[2] if len(parts) > 2 else "*"

        if (q_prod in ("*", prod)) and (q_doc in ("*", doc)) and (q_lang in ("*", lang)):
            return True
    return False


def expand_and_filter_deliverables(
    base_deliverables: list[Deliverable], doctypes: tuple[str, ...]
) -> list[DisplayDeliverable]:
    """Project English blueprints to translated locales and filter by user query."""
    expanded_dict: dict[tuple[str, str, str, str], DisplayDeliverable] = {}

    # Pass 1: Project en-us blueprints FIRST
    for d in base_deliverables:
        native_lang = str(d.xml.lang)
        prod = d.xml.product_id or ""
        doc = d.xml.docset_path or ""
        d_id = d.xml.deliverableid or ""

        if native_lang == "en-us" and d.xml.translations:
            for t_lang in d.xml.translations:
                t_key = (prod, doc, t_lang, d_id)
                if t_key not in expanded_dict:
                    expanded_dict[t_key] = DisplayDeliverable(d, t_lang, True)

    # Pass 2: Add native deliverables (overriding blueprints if they explicitly collide)
    for d in base_deliverables:
        native_lang = str(d.xml.lang)
        prod = d.xml.product_id or ""
        doc = d.xml.docset_path or ""
        d_id = d.xml.deliverableid or ""

        key = (prod, doc, native_lang, d_id)
        expanded_dict[key] = DisplayDeliverable(d, native_lang, False)

    expanded_deliverables = list(expanded_dict.values())

    # Pass 3: Filter to EXACT user query
    if not doctypes:
        return expanded_deliverables

    return [dd for dd in expanded_deliverables if _matches_query(dd, doctypes)]


async def async_list_cmd(
    ctx: DocBuildContext,
    doctypes: tuple[str, ...],
    console: Console,
    show_trans: bool,
    show_formats: bool,
    show_categories: bool,
    repo_format: str | None,
    flat: bool,
) -> None:
    """Async worker to fetch the XML, parse Doctypes, and build the tree."""
    parsed_doctypes = parse_doctypes(doctypes, console)

    # 2. Get XML Tree
    assert ctx.envconfig is not None
    portal_xml_path = ctx.envconfig.paths.main_portal_config.expanduser()

    try:
        tree = await parse_portal_config(portal_xml_path)
    except (OSError, etree.XMLSyntaxError, etree.XIncludeError) as e:
        console.print(f"[red]Error loading XML schema:[/red] {e}")
        raise click.Abort() from e

    if parsed_doctypes:
        validate_docsets_against_xml(parsed_doctypes, tree, console)

    # --- 3. Fetch Broad Deliverables ---
    if doctypes:
        broad_strs = []
        for dt_str in doctypes:
            parts = dt_str.split("/")
            prod = parts[0]
            doc = parts[1] if len(parts) > 1 else "*"
            broad_strs.append(f"{prod}/{doc}/*")
        broad_doctypes = parse_doctypes(tuple(broad_strs), console)
        all_nodes = list_all_deliverables(tree, broad_doctypes)
    else:
        all_nodes = tree.xpath("//deliverable")

    base_deliverables = [Deliverable(_node=node) for node in all_nodes]

    # --- 4. Expand Inherited Deliverables & Filter ---
    final_deliverables = expand_and_filter_deliverables(base_deliverables, doctypes)

    if not final_deliverables:
        console.print("[yellow]No deliverables found matching the criteria.[/yellow]")
        return

    if flat:
        print_flat(final_deliverables, console, show_trans, show_formats, show_categories, repo_format)
    else:
        hierarchy = build_hierarchy(final_deliverables)
        print_hierarchy(hierarchy, console, show_trans, show_formats, show_categories, repo_format)


@click.command(name="list")
@click.option("--trans", "-T", is_flag=True, help="List available translations.")
@click.option("--formats", "-F", is_flag=True, help="List available output formats.")
@click.option("--categories", "-C", is_flag=True, help="List categories.")
@click.option(
    "--repo",
    "-R",
    type=click.Choice(["short", "long"]),
    default=None,
    help="List repository origin (requires 'short' or 'long')."
)
@click.option("--flat", is_flag=True, help="Display the output as a flat list.")
@click.argument("doctypes", nargs=-1)
@click.pass_obj
def list_cmd(
    ctx: DocBuildContext,
    doctypes: tuple[str, ...],
    trans: bool,
    formats: bool,
    categories: bool,
    repo: str | None,
    flat: bool,
) -> None:
    """List products, docsets, and deliverables from the portal config.

    Accepts optional DOCTYPE arguments to filter the output.
    Format: PRODUCT/DOCSETS[@LIFECYCLES]/LANGS

    Example:
        docbuild portal list sles/15-SP6

    \f

    :param ctx: The DocBuildContext passed from the CLI, containing config and options.
    :param doctypes: A tuple of doctype strings passed as arguments to the command.
    :param trans: Show translation metadata.
    :param formats: Show output formats metadata.
    :param categories: Show categories metadata.
    :param repo: Show repository origin (short or long).
    :param flat: Display a flat list instead of a hierarchy tree.

    """ # noqa: D301
    console = Console()

    async def main() -> None:
        await asyncio.create_task(
            async_list_cmd(ctx, doctypes, console, trans, formats, categories, repo, flat),
            name="portal-list",
        )

    asyncio.run(main())
