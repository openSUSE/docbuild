"""Portal management commands for the docbuild CLI."""

import asyncio
from collections.abc import Sequence

import click
from lxml import etree  # type: ignore
from rich.console import Console
from rich.tree import Tree

from ...cli.console import console as shared_console
from ...cli.context import DocBuildContext
from ...config.xml.list import list_all_deliverables
from ...models.deliverable import Deliverable
from ...models.doctype import Doctype
from ...models.product import Product
from ...tasks.portal import parse_portal_config


def _matches_doctype(prod: str, doc: str, lang: str, doctypes: Sequence[Doctype] | None) -> bool:
    """Check if a generated deliverable matches the requested doctype queries."""
    if not doctypes:
        return True
    dt_str = f"{prod or '*'}/{doc or '*'}/{lang}"
    deliv_dt = Doctype.from_str(dt_str)
    return any(deliv_dt in dt for dt in doctypes)


def expand_deliverables(
    deliverables: list[Deliverable],
    doctypes: Sequence[Doctype] | None = None,
) -> list[tuple[str, Deliverable]]:
    """Project English blueprints to translated locales and filter by doctype."""
    # Pass 1: Identify explicit native overrides to prevent blueprint collision
    native_keys = {
        (str(d.xml.lang), d.xml.product_id or "", d.xml.docset_path or "", d.xml.deliverableid or "")
        for d in deliverables
        if str(d.xml.lang) != "en-us"
    }

    results = []

    # Pass 2: Iterate in strict XML sequence to preserve author order
    for d in deliverables:
        prod = d.xml.product_id or ""
        doc = d.xml.docset_path or ""
        d_id = d.xml.deliverableid or ""
        native_lang = str(d.xml.lang)

        # 1. Project blueprints
        if native_lang == "en-us" and d.xml.translations:
            for t_lang in d.xml.translations:
                if (t_lang, prod, doc, d_id) in native_keys:
                    continue  # Skip if native override exists

                if _matches_doctype(prod, doc, t_lang, doctypes):
                    results.append((t_lang, d))

        # 2. Add native deliverable
        if _matches_doctype(prod, doc, native_lang, doctypes):
            results.append((native_lang, d))

    return results


def parse_doctypes(doctypes: tuple[str, ...], console: Console) -> list[Doctype] | None:
    """Parse raw CLI arguments into Doctype objects with default fallbacks."""
    if not doctypes:
        return None

    parsed_doctypes = []
    for dt in doctypes:
        if "/" not in dt:
            dt = f"{dt}/*"

        try:
            parsed_doctypes.append(Doctype.from_str(dt))
        except ValueError as e:
            console.print(f"[error]Error parsing doctype:[/error] {e}")
            raise click.Abort() from e

    return parsed_doctypes


def get_display_name(deliv: Deliverable, lang: str) -> str:
    """Determine the main display name for a deliverable."""
    d_id = deliv.xml.deliverableid
    dc_file = deliv.xml.dcfile

    if deliv.xml.is_prebuilt:
        title_node = deliv.xml.node.find("title")
        title = title_node.text if title_node is not None else (d_id or "unnamed-deliverable")
        base = f"{title} (Prebuilt)"
    else:
        d_id_str = d_id or "unnamed-deliverable"
        base = f"{d_id_str} ({dc_file})" if dc_file else d_id_str

        # Only override for docset xrefs (which lack a deliverable ID and DC file)
        if deliv.xml.node.get("type") == "xref" and not d_id and not dc_file:
            xref_node = deliv.xml.node.find("xref")
            linkend = xref_node.get("linkend") if xref_node is not None else "unknown-target"
            base = f"{linkend} (xref)"

    if str(deliv.xml.lang) != lang:
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


def build_deliverable_tree(
    title: str,
    deliv: Deliverable,
    lang: str,
    show_trans: bool,
    show_formats: bool,
    show_categories: bool,
    repo_format: str | None,
) -> Tree:
    """Build a Tree node for a deliverable and append requested metadata."""
    deliv_branch = Tree(title)

    if deliv.xml.is_prebuilt:
        for url_node in deliv.xml.node.xpath("prebuilt/url"):
            if href := url_node.get("href"):
                deliv_branch.add(f"URL: [link={href}]{href}[/link]")

    if show_trans:
        append_translations(deliv_branch, deliv, lang)
    if show_formats:
        append_formats(deliv_branch, deliv)
    if show_categories:
        append_categories(deliv_branch, deliv)
    if repo_format:
        append_repo(deliv_branch, deliv, repo_format)

    return deliv_branch


def _group_into_hierarchy(items: list[tuple[str, Deliverable]]) -> dict[str, dict[str, dict[str, list[Deliverable]]]]:
    """Group deliverables into a nested dictionary while preserving insertion order."""
    hierarchy: dict[str, dict[str, dict[str, list[Deliverable]]]] = {}
    for lang, deliv in items:
        prod = deliv.xml.product_id or "unknown-product"
        doc = deliv.xml.docset_path or "unknown-docset"

        if lang not in hierarchy:
            hierarchy[lang] = {}
        if prod not in hierarchy[lang]:
            hierarchy[lang][prod] = {}
        if doc not in hierarchy[lang][prod]:
            hierarchy[lang][prod][doc] = []

        hierarchy[lang][prod][doc].append(deliv)
    return hierarchy


def print_hierarchy(
    items: list[tuple[str, Deliverable]],
    console: Console,
    show_trans: bool,
    show_formats: bool,
    show_categories: bool,
    repo_format: str | None,
) -> None:
    """Render and print the nested hierarchy as a Rich Tree."""
    hierarchy = _group_into_hierarchy(items)

    for lang, products in sorted(hierarchy.items()):
        root_tree = Tree(f"[lang]{lang}/[/]")

        for product, docsets in sorted(products.items()):
            prod_branch = root_tree.add(f"[product]{product}[/]")

            for docset, delivs in sorted(docsets.items()):
                docset_branch = prod_branch.add(f"[docset]{docset}[/]")

                # Iterate directly in XML sequence (NO alphabetical sorting!)
                for deliv in delivs:
                    display_name = get_display_name(deliv, lang)
                    deliv_branch = build_deliverable_tree(
                        display_name,
                        deliv,
                        lang,
                        show_trans,
                        show_formats,
                        show_categories,
                        repo_format,
                    )
                    docset_branch.add(deliv_branch)

        console.print(root_tree)
        console.print()


def print_flat(
    items: list[tuple[str, Deliverable]],
    console: Console,
    show_trans: bool,
    show_formats: bool,
    show_categories: bool,
    repo_format: str | None,
) -> None:
    """Render and print the deliverables as a flat list."""
    hierarchy = _group_into_hierarchy(items)

    for lang, products in sorted(hierarchy.items()):
        for product, docsets in sorted(products.items()):
            for docset, delivs in sorted(docsets.items()):

                # Iterate directly in XML sequence (No alphabetical sorting)
                for deliv in delivs:
                    display_name = get_display_name(deliv, lang)
                    flat_title = f"[lang]{lang}[/]/[product]{product}[/]/[docset]{docset}[/]:{display_name}"

                    deliv_tree = build_deliverable_tree(
                        flat_title,
                        deliv,
                        lang,
                        show_trans,
                        show_formats,
                        show_categories,
                        repo_format,
                    )
                    console.print(deliv_tree if deliv_tree.children else flat_title)


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
        console.print(f"[error]Error parsing doctype:[/error] {err_count} validation {noun} for Doctype:\n")
        for err in errors:
            console.print(err)
        raise click.Abort()


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
        console.print(f"[error]Error loading XML schema:[/error] {e}")
        raise click.Abort() from e

    if parsed_doctypes:
        validate_docsets_against_xml(parsed_doctypes, tree, console)

    # --- 3. Fetch Broad Deliverables ---
    if doctypes:
        # Broaden to all languages to fetch en-us blueprints along with targets
        broad_strs = []
        for dt_str in doctypes:
            parts = dt_str.split("/")
            prod = parts[0]
            doc = parts[1] if len(parts) > 1 else "*"
            broad_strs.append(f"{prod}/{doc}/*")
        broad_doctypes = parse_doctypes(tuple(broad_strs), console)
        all_nodes = list_all_deliverables(tree, broad_doctypes)
    else:
        # Fetch all deliverables across all products, docsets, and locales
        all_nodes = list_all_deliverables(tree, [Doctype.from_str("//*")])

    base_deliverables = [Deliverable(_node=node) for node in all_nodes]

    # --- 4. Expand Inherited Deliverables & Filter ---
    final_deliverables = expand_deliverables(base_deliverables, parsed_doctypes)

    if not final_deliverables:
        console.print("[warning]No deliverables found matching the criteria.[/warning]")
        return

    if flat:
        print_flat(final_deliverables, console, show_trans, show_formats, show_categories, repo_format)
    else:
        print_hierarchy(final_deliverables, console, show_trans, show_formats, show_categories, repo_format)


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
    console = shared_console

    async def main() -> None:
        await asyncio.create_task(
            async_list_cmd(ctx, doctypes, console, trans, formats, categories, repo, flat),
            name="portal-list",
        )

    asyncio.run(main())
