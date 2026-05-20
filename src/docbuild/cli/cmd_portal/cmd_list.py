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
) -> dict[str, dict[str, dict[str, list[str]]]]:
    """Group a list of Deliverable domain objects into a nested dictionary structure.

    :param deliverables: A list of Deliverable models to organize.
    :return: A nested dictionary structured as {lang: {product: {docset: [deliverable titles]}}}.
    """
    hierarchy: dict[str, dict[str, dict[str, list[str]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )

    for deliverable in deliverables:
        # Pull facts via the clean Deliverable XML view facade
        lang = str(deliverable.xml.lang)
        product = deliverable.xml.productid or "unknown-product"
        docset = deliverable.xml.docsetid or "unknown-docset"

        # Determine a compact leaf string using ID and DC file metadata
        d_id = deliverable.xml.node.get("id", "unnamed-deliverable")
        dc_file = deliverable.xml.dcfile
        display_name = f"{d_id} ({dc_file})" if dc_file else d_id

        hierarchy[lang][product][docset].append(display_name)

    return hierarchy


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


def _print_hierarchy(hierarchy: dict[str, dict[str, dict[str, list[str]]]], console: Console) -> None:
    """Render and print the nested hierarchy as a Rich Tree."""
    for lang, products in sorted(hierarchy.items()):
        root_tree = Tree(f"[bold blue]{lang}/[/bold blue]")

        for product, docsets in sorted(products.items()):
            prod_branch = root_tree.add(f"[bold]{product}[/bold]")

            for docset, delivs in sorted(docsets.items()):
                docset_branch = prod_branch.add(f"[cyan]{docset}[/cyan]")

                for display_name in sorted(delivs):
                    docset_branch.add(display_name)

        console.print(root_tree)
        console.print()


async def async_list_cmd(ctx: DocBuildContext, doctypes: tuple[str, ...], console: Console) -> None:
    """Async worker to fetch the XML, parse Doctypes, and build the tree.

    :param ctx: The DocBuildContext containing CLI options and config.
    :param doctypes: A tuple of doctype strings passed as arguments to the command.
    :param console: The Rich Console object for outputting the tree.
    """
    # 1. Parse Doctypes
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

    # 4. Group data for Rich Tree
    hierarchy = build_hierarchy(deliverables)

    # 5. Build and print the Rich Tree
    _print_hierarchy(hierarchy, console)


@click.command(name="list")
@click.argument("doctypes", nargs=-1)
@click.pass_obj
def list_cmd(ctx: DocBuildContext, doctypes: tuple[str, ...]) -> None:
    r"""List products, docsets, and deliverables from the portal config.

    Accepts optional DOCTYPE arguments to filter the output.
    Format: [PRODUCT]/[DOCSETS]@[LIFECYCLES]/[LANGS]

    Example:
        docbuild portal list sles/15-SP6

    \f

    :param ctx: The DocBuildContext passed from the CLI, containing config and options.
    :param doctypes: A tuple of doctype strings passed as arguments to the command.

    """
    console = Console()
    asyncio.run(async_list_cmd(ctx, doctypes, console))
