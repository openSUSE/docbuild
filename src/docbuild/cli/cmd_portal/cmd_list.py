"""Portal management commands for the docbuild CLI."""

import asyncio
from collections import defaultdict

import click
from lxml import etree  #type: ignore
from rich.console import Console
from rich.tree import Tree

from docbuild.cli.context import DocBuildContext
from docbuild.config.xml.list import list_all_deliverables
from docbuild.models.doctype import Doctype


def build_hierarchy(
    deliverables: list[etree._Element],
) -> dict[str, dict[str, dict[str, list[str]]]]:
    """Group a flat list of deliverable nodes into a nested dictionary.

    :param deliverables: A list of <deliverable> XML nodes to organize.
    :return: A nested dictionary structured as {lang: {product: {docset: [deliverable titles]}}}}.
    """
    # TODO: Refactor this to use `list[Deliverable]` once PR #253 is merged.
    # We should avoid manual XML tree traversal (getparent) here and instead
    # rely on the new Deliverable public API properties (language, product, docset).
    hierarchy: dict[str, dict[str, dict[str, list[str]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )

    for d_node in deliverables:
        # Walk up the XML tree: deliverable -> language -> builddocs -> docset -> product
        lang_node = d_node.getparent()
        builddocs_node = lang_node.getparent() if lang_node is not None else None
        docset_node = builddocs_node.getparent() if builddocs_node is not None else None
        product_node = docset_node.getparent() if docset_node is not None else None

        lang = lang_node.get("lang", "unknown-lang") if lang_node is not None else "unknown-lang"
        product = product_node.get("productid", "unknown-product") if product_node is not None else "unknown-product"
        docset = docset_node.get("setid", "unknown-docset") if docset_node is not None else "unknown-docset"

        # Try to use title, fallback to id
        d_id = d_node.get("id", "unnamed-deliverable")
        title_node = d_node.find("title")
        title = title_node.text if title_node is not None and title_node.text else d_id

        hierarchy[lang][product][docset].append(title)

    return hierarchy


async def async_list_cmd(ctx: DocBuildContext, doctypes: tuple[str, ...], console: Console) -> None:
    """Async worker to fetch the XML, parse Doctypes, and build the tree.

    :param ctx: The DocBuildContext containing CLI options and config.
    :param doctypes: A tuple of doctype strings passed as arguments to the command.
    :param console: The Rich Console object for outputting the tree.
    """
    # 1. Parse Doctypes
    parsed_doctypes = None
    if doctypes:
        try:
            parsed_doctypes = [Doctype.from_str(dt) for dt in doctypes]
        except ValueError as e:
            console.print(f"[red]Error parsing doctype:[/red] {e}")
            raise click.Abort() from e

    # 2. Get XML Tree
    config_dir = ctx.envconfig.paths.config_dir.expanduser() # type: ignore

    # TODO: Once Issue #231 is merged, we can replace this hardcoded string with:
    # portal_cfg_name = ctx.envconfig.paths.main_portal_config
    # portal_xml_path = config_dir / portal_cfg_name
    portal_xml_path = config_dir / "portal.xml"

    if not portal_xml_path.exists():
        console.print(f"[red]Error: Main portal config not found at {portal_xml_path}[/red]")
        raise click.Abort()

    try:
        # TODO: Refactor this into a dedicated `create_portal_config()` helper function
        # to centralize Portal XML loading, rather than doing raw etree parsing in the CLI.
        tree = etree.parse(portal_xml_path)
        tree.xinclude()
    except Exception as e:
        console.print(f"[red]Error loading XML schema:[/red] {e}")
        raise click.Abort() from e

    # 3. Fetch Deliverables
    deliverables = list(list_all_deliverables(tree, parsed_doctypes))

    if not deliverables:
        console.print("[yellow]No deliverables found matching the criteria.[/yellow]")
        return

    # 4. Group data for Rich Tree
    hierarchy = build_hierarchy(deliverables)

    # 5. Build and print the Rich Tree
    for lang, products in sorted(hierarchy.items()):
        root_tree = Tree(f"[bold blue]{lang}/[/bold blue]")

        for product, docsets in sorted(products.items()):
            prod_branch = root_tree.add(f"[bold]{product}[/bold]")

            for docset, delivs in sorted(docsets.items()):
                docset_branch = prod_branch.add(f"[cyan]{docset}[/cyan]")

                for title in sorted(delivs):
                    docset_branch.add(title)

        console.print(root_tree)
        console.print()


@click.command(name="list")
@click.argument("doctypes", nargs=-1)
@click.pass_obj
def list_cmd(ctx: DocBuildContext, doctypes: tuple[str, ...]) -> None:
    """List products, docsets, and deliverables from the portal config.

    Accepts optional DOCTYPE arguments to filter the output.
    Format: [PRODUCT]/[DOCSETS]@[LIFECYCLES]/[LANGS]

    Example:
        docbuild portal list sles/15-SP6

    :param ctx: The DocBuildContext passed from the CLI, containing config and options.
    :param doctypes: A tuple of doctype strings passed as arguments to the command.

    """
    console = Console()
    asyncio.run(async_list_cmd(ctx, doctypes, console))
