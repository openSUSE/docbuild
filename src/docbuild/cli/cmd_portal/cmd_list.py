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
from ...constants import DEFAULT_LANG
from ...models.deliverable import Deliverable
from ...models.doctype import Doctype
from ...models.product import Product, ProductCatalog
from ...tasks.portal import parse_portal_config
from ..completion import collect_docsets, complete_doctypes


def matches_doctype(prod: str, doc: str, lang: str, doctypes: Sequence[Doctype] | None) -> bool:
    """Check if a generated deliverable matches the requested doctype queries.

    The lifecycle is not part of the check.

    :param prod: Product ID. An empty string is treated as ``*``.
    :param doc: Docset path. An empty string is treated as ``*``.
    :param lang: Language code, for example ``en-us``.
    :param doctypes: Doctypes to match against.
    :return: ``True`` if one of the doctypes matches or if none are given.
    :raises ValueError: If the values do not form a valid doctype.

    .. code-block:: pycon

        >>> wanted = [Doctype.from_str("sles/*/en-us")]
        >>> matches_doctype("sles", "15-SP6", "en-us", wanted)
        True
        >>> matches_doctype("smart", "15-SP6", "en-us", wanted)
        False
    """
    if not doctypes:
        return True
    dt_str = f"{prod or '*'}/{doc or '*'}/{lang}"
    deliv_dt = Doctype.from_str(dt_str)
    return any(deliv_dt in dt for dt in doctypes)


def expand_deliverables(
    deliverables: list[Deliverable],
    doctypes: Sequence[Doctype] | None = None,
) -> list[tuple[str, Deliverable]]:
    """Project English blueprints to translated locales and filter by doctype.

    An English deliverable is also listed for each of its translations,
    unless that language has its own deliverable with the same ID.
    The deliverables stay in the same order as in the XML.

    :param deliverables: Deliverables in XML order.
    :param doctypes: Doctypes to filter by. Nothing is filtered if empty.
    :return: Pairs of language and deliverable, for example
        ``("en-us", deliverable)``.
    :raises ValueError: If a deliverable does not form a valid doctype while
        filtering.
    """
    # Pass 1: Identify explicit native overrides to prevent blueprint collision
    native_keys = {
        (str(d.xml.lang), d.xml.product_id or "", d.xml.docset_path or "", d.xml.deliverableid or "")
        for d in deliverables
        if str(d.xml.lang) != DEFAULT_LANG
    }

    results = []

    # Pass 2: Iterate in strict XML sequence to preserve author order
    for d in deliverables:
        prod = d.xml.product_id or ""
        doc = d.xml.docset_path or ""
        d_id = d.xml.deliverableid or ""
        native_lang = str(d.xml.lang)

        # 1. Project blueprints
        if native_lang == DEFAULT_LANG and d.xml.translations:
            for t_lang in d.xml.translations:
                if t_lang == native_lang or (t_lang, prod, doc, d_id) in native_keys:
                    continue

                if matches_doctype(prod, doc, t_lang, doctypes):
                    results.append((t_lang, d))

        # 2. Add native deliverable
        if matches_doctype(prod, doc, native_lang, doctypes):
            results.append((native_lang, d))

    return results


def parse_doctypes(doctypes: tuple[str, ...], console: Console) -> list[Doctype] | None:
    """Parse raw CLI arguments into Doctype objects with default fallbacks.

    An argument without a slash selects all docsets of that product.
    The language is ``en-us`` if none is given.

    :param doctypes: Doctype strings from the command line.
    :param console: Console to print parsing errors to.
    :return: The parsed doctypes, or ``None`` if there are no arguments.
    :raises click.Abort: If an argument is not a valid doctype.

    .. code-block:: pycon

        >>> [str(dt) for dt in parse_doctypes(("sles",), Console())]
        ['sles/*@unknown/en-us']
    """
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
    """Determine the main display name for a deliverable.

    Prebuilt deliverables show their title, others show their ID and DC file.
    An xref with no ID and no DC file shows its link target.

    :param deliv: The deliverable.
    :param lang: Language the deliverable is listed under, for example
        ``en-us``.
    :return: The name to show. It ends in ``[en-us blueprint]`` if ``lang``
        differs from the language of the deliverable.
    """
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
    """Append translation metadata to the deliverable branch.

    Nothing is added if there are no other languages.

    :param deliv_branch: Tree branch to add the line to.
    :param deliv: The deliverable.
    :param lang: Language to leave out of the list, for example ``en-us``.
    """
    other_langs = sorted(other_lang for other_lang in deliv.xml.translations if other_lang != lang)
    if other_langs:
        deliv_branch.add(f"Translations: {', '.join(other_langs)}")


def append_formats(deliv_branch: Tree, deliv: Deliverable) -> None:
    """Append output formats metadata to the deliverable branch.

    Only enabled formats are listed.

    :param deliv_branch: Tree branch to add the line to.
    :param deliv: The deliverable.
    """
    if attrs := deliv.xml.format_attrs():
        fmt_names = {"pdf": "PDF", "html": "HTML", "single-html": "Single-HTML", "epub": "EPUB"}
        available = [fmt_names.get(k, k.upper()) for k, v in attrs.items() if v]
        if available:
            deliv_branch.add(f"Formats: {', '.join(available)}")


def append_categories(deliv_branch: Tree, deliv: Deliverable) -> None:
    """Append category metadata to the deliverable branch.

    Nothing is added if the deliverable has no category.

    :param deliv_branch: Tree branch to add the line to.
    :param deliv: The deliverable.
    """
    if cat_title := deliv.xml.category_title:
        deliv_branch.add(f"Category: {cat_title}")


def append_repo(deliv_branch: Tree, deliv: Deliverable, repo_format: str) -> None:
    """Append repository metadata to the deliverable branch.

    Nothing is added if the deliverable has no repository. A remote repository
    URL that cannot be parsed is shown as it is.

    :param deliv_branch: Tree branch to add the line to.
    :param deliv: The deliverable.
    :param repo_format: ``long`` shows the full URL, any other value shows
        the short form.
    """
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
    """Build a Tree node for a deliverable and append requested metadata.

    URLs of prebuilt deliverables are always added.

    :param title: Text of the node.
    :param deliv: The deliverable.
    :param lang: Language the deliverable is listed under, for example
        ``en-us``.
    :param show_trans: Show the translations.
    :param show_formats: Show the output formats.
    :param show_categories: Show the category.
    :param repo_format: Show the repository as ``short`` or ``long``.
        Not shown if ``None``.
    :return: The updated tree node.
    """
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


def group_into_hierarchy(items: list[tuple[str, Deliverable]]) -> dict[str, dict[str, dict[str, list[Deliverable]]]]:
    """Group deliverables into a nested dictionary while preserving insertion order.

    A missing product or docset is grouped as ``unknown-product`` or
    ``unknown-docset``.

    :param items: Pairs of language and deliverable.
    :return: Deliverables grouped by language, product, and docset.
    """
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
    """Render and print the nested hierarchy as a Rich Tree.

    Each language gets its own tree. Languages, products, and docsets are
    sorted, but deliverables keep their XML order.

    :param items: Pairs of language and deliverable.
    :param console: Console to print to.
    :param show_trans: Show the translations.
    :param show_formats: Show the output formats.
    :param show_categories: Show the category.
    :param repo_format: Show the repository as ``short`` or ``long``.
        Not shown if ``None``.
    """
    hierarchy = group_into_hierarchy(items)

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
    """Render and print the deliverables as a flat list.

    The order is the same as in :func:`print_hierarchy`. Requested details
    are printed below each deliverable.

    :param items: Pairs of language and deliverable.
    :param console: Console to print to.
    :param show_trans: Show the translations.
    :param show_formats: Show the output formats.
    :param show_categories: Show the category.
    :param repo_format: Show the repository as ``short`` or ``long``.
        Not shown if ``None``.
    """
    hierarchy = group_into_hierarchy(items)

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


def find_unknown_product_errors(
    doctypes: list[Doctype],
    catalog: ProductCatalog,
) -> list[str]:
    """Return formatted error messages for product acronyms missing from *catalog*."""
    found: list[str] = []
    for dt in doctypes:
        if dt.product and dt.product != Product.ALL:
            prod_val = dt.product.acronym
            if prod_val not in catalog:
                suggestions = catalog.suggest(prod_val)
                hint = (
                    f" Did you mean: {', '.join(repr(s) for s in suggestions)}?"
                    if suggestions
                    else ""
                )
                found.append(f"* '{prod_val}' is not a known Product.{hint}")
    return found


def validate_docsets_against_xml(
    doctypes: list[Doctype],
    tree: etree._ElementTree | etree._Element,
    console: Console,
    catalog: ProductCatalog | None = None,
) -> None:
    """Dynamically validate that provided docsets exist for their respective products.

    Doctypes with a wildcard product or docset are not checked.
    All errors are printed before aborting.

    :param doctypes: Doctypes to check.
    :param tree: The parsed portal config.
    :param console: Console to print errors to.
    :raises click.Abort: If any docset does not exist.
    """
    errors = []

    errors: list[str] = []
    if catalog is not None:
        errors.extend(find_unknown_product_errors(doctypes, catalog))

    for dt in doctypes:
        if dt.product and dt.product != Product.ALL and dt.docset and "*" not in dt.docset:
            prod_val = dt.product.acronym
            valid_docsets = collect_docsets(tree, prod_val)

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
    """Async worker to fetch the XML, parse Doctypes, and build the tree.

    Deliverables are read in all languages first, because translations
    come from the English ones. The language filter is applied afterwards.

    :param ctx: Context with the loaded environment config.
    :param doctypes: Doctype strings from the command line.
    :param console: Console to print to.
    :param show_trans: Show the translations.
    :param show_formats: Show the output formats.
    :param show_categories: Show the category.
    :param repo_format: Show the repository as ``short`` or ``long``.
        Not shown if ``None``.
    :param flat: Print a flat list instead of a tree.
    :raises click.Abort: If a doctype or docset is invalid, or if the portal
        config cannot be loaded.
    """
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
@click.argument("doctypes", nargs=-1, shell_complete=complete_doctypes)
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
    :raises click.Abort: If the arguments or the portal config are invalid.

    """ # noqa: D301
    console = shared_console

    async def main() -> None:
        """Run the list command as a named task."""
        await asyncio.create_task(
            async_list_cmd(ctx, doctypes, console, trans, formats, categories, repo, flat),
            name="portal-list",
        )

    asyncio.run(main())
