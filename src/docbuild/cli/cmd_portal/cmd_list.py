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
) -> dict[str, dict[str, dict[str, list[Deliverable]]]]:
    """Group Deliverables into a hierarchy.

    :param deliverables: A list of Deliverable models to organize.
    :return: A hierarchy_dict mapping lang -> product -> docset -> deliverables.
    """
    hierarchy: dict[str, dict[str, dict[str, list[Deliverable]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )

    for deliv in deliverables:
        lang = str(deliv.xml.lang)
        product = deliv.xml.productid or "unknown-product"
        docset = deliv.xml.docsetid or "unknown-docset"

        hierarchy[lang][product][docset].append(deliv)

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


def get_display_name(deliv: Deliverable, d_id: str) -> str:
    """Determine the main display name for a deliverable."""
    if deliv.xml.is_prebuilt:
        title_node = deliv.xml.node.find("title")
        title = title_node.text if title_node is not None else d_id
        return f"{title} (Prebuilt)"

    dc_file = deliv.xml.dcfile
    return f"{d_id} ({dc_file})" if dc_file else d_id


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
    deliv: Deliverable,
    lang: str,
    show_trans: bool,
    show_formats: bool,
    show_categories: bool,
    repo_format: str | None,
) -> None:
    """Format and append a single deliverable node to the Rich Tree."""
    d_id = deliv.xml.node.get("id", "unnamed-deliverable")

    # 1. Format the main display name
    display_name = get_display_name(deliv, d_id)
    deliv_branch = docset_branch.add(display_name)

    # 2. Automatically show URLs for prebuilt deliverables
    if deliv.xml.is_prebuilt:
        for url_node in deliv.xml.node.xpath("prebuilt/url"):
            if href := url_node.get("href"):
                deliv_branch.add(f"URL: [link={href}]{href}[/link]")

    # 3. Add Optional Metadata based on CLI Flags
    if show_trans:
        append_translations(deliv_branch, deliv, lang)
    if show_formats:
        append_formats(deliv_branch, deliv)
    if show_categories:
        append_categories(deliv_branch, deliv)
    if repo_format:
        append_repo(deliv_branch, deliv, repo_format)


def print_hierarchy(
    hierarchy: dict[str, dict[str, dict[str, list[Deliverable]]]],
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
                    build_deliverable_branch(
                        docset_branch,
                        deliv,
                        lang,
                        show_trans,
                        show_formats,
                        show_categories,
                        repo_format,
                    )

        console.print(root_tree)
        console.print()


def validate_docsets_against_xml(
    doctypes: list[Doctype], tree: etree._ElementTree | etree._Element, console: Console
) -> None:
    """Dynamically validate that provided docsets exist for their respective products."""
    errors = []

    for dt in doctypes:
        if dt.product and "*" not in dt.product and dt.docset and "*" not in dt.docset:
            prod_val = dt.product.value
            
            # Use the class's own string parser to bypass strict __init__ type-checking issues
            broad_dt = Doctype.from_str(f"{prod_val}/*/*")
            
            # Harvest all valid docset IDs using the Deliverable abstraction
            valid_docsets = set()
            for node in list_all_deliverables(tree, [broad_dt]):
                deli = Deliverable(_node=node)
                if deli.xml.docsetid:
                    valid_docsets.add(deli.xml.docsetid)

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
    parsed_doctypes = parse_doctypes(doctypes, console)

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

    if parsed_doctypes:
        validate_docsets_against_xml(parsed_doctypes, tree, console)

    # 3. Fetch and wrap Deliverables into Domain Objects
    # Consuming the generator directly saves memory over converting to an intermediate list
    deliverables = [
        Deliverable(_node=node)
        for node in list_all_deliverables(tree, parsed_doctypes)
    ]

    if not deliverables:
        console.print("[yellow]No deliverables found matching the criteria.[/yellow]")
        return

    hierarchy = build_hierarchy(deliverables)

    print_hierarchy(
        hierarchy,
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
    default=None,
    help="List repository origin (requires 'short' or 'long')."
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
    :param repo: Show repository metadata (short or long).

    """ # noqa: D301
    console = Console()
    asyncio.run(async_list_cmd(ctx, doctypes, console, trans, formats, categories, repo))

