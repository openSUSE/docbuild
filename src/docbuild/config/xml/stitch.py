"""Stitch file handling."""

import asyncio
from collections import Counter
from collections.abc import Callable, Sequence
from copy import deepcopy
import importlib
import inspect
import logging
from pathlib import Path
import resource
import sys

from lxml import etree

from .references import check_stitched_references

log = logging.getLogger(__name__)


def load_check_functions() -> list[Callable]:
    """Load all check functions from :mod:`docbuild.config.xml.checks`."""
    xmlchecks = importlib.import_module("docbuild.config.xml.checks")

    return [
        func
        for name, func in inspect.getmembers(xmlchecks, inspect.isfunction)
        if name.startswith("check_")
    ]


def log_memory_usage() -> int:
    """Determine the memory usage.

    :return: memory usage in kilobytes
    """
    # Get the resource usage for the current process (RUSAGE_SELF)
    usage = resource.getrusage(resource.RUSAGE_SELF)
    # usage.ru_maxrss returns the memory.
    # Note: On Linux, this is usually Kilobytes. On macOS, it is Bytes.
    memory_in_kb = usage.ru_maxrss

    # Adjustment for macOS to keep units consistent (convert to KB)
    if sys.platform == "darwin":
        # Use integer division to match the function's return type hint
        memory_in_kb //= 1024

    return memory_in_kb


def check_stitchfile(tree: etree._Element | etree._ElementTree) -> bool:
    """Check the stitchfile for unresolved references.

    :param tree: The tree of the stitched XML file.
    :returns: True if no unresolved references are found, False otherwise.
    """
    result = check_stitched_references(tree)

    for err in result:
        log.error(err)

    return not bool(result)


async def create_stitchfile(
    xmlfiles: Sequence[str | Path],
    *,
    xmlparser: etree.XMLParser | None = None,
    with_ref_check: bool = True,
) -> etree._ElementTree:
    """Asynchronously create a stitch file from a list of XML files.

    :param xmlfiles: A sequence of XML file paths to stitch together.
    :param xmlparser: An optional XML parser to use.
    :param with_ref_check: Whether to perform a reference check (=True) or not (=False).
    :return: all XML file stitched together into a
        :class:`lxml.etree.ElementTree` object.
    """
    # TODO: Should we retrieve them from the config file?
    # simplify_xslt = XMLDATADIR / 'simplify.xsl'

    # TODO: Do we need the MD5 hashes? If so maybe store them

    async def parse_and_xinclude(file_path: Path) -> etree._ElementTree:
        """Parse a single XML file and run XInclude in a thread."""
        tree = await asyncio.to_thread(etree.parse, file_path, xmlparser)
        await asyncio.to_thread(tree.xinclude)
        return tree

    # Step 1: Concurrently parse all XML files
    docservconfig = etree.Element("docservconfig", attrib=None, nsmap=None)
    tasks = [parse_and_xinclude(Path(xmlfile)) for xmlfile in xmlfiles]
    parsed_trees = await asyncio.gather(*tasks)

    for tree in parsed_trees:
        # The deepcopy is unfortunately necessary to avoid
        # the "free(): invalid pointer" error
        docservconfig.append(deepcopy(tree.getroot()))
        del tree  # Explicitly delete the tree to free memory

    # Step 2: Check for unique IDs
    product_ids = docservconfig.xpath("//@productid")
    if len(product_ids) > len(set(product_ids)):
        duplicates = [item for item, count in Counter(product_ids).items() if count > 1]
        raise ValueError(f"Duplicate product IDs found: {', '.join(duplicates)}")

    # Step 3: Check references
    if with_ref_check:
        result = check_stitchfile(docservconfig)
        if not result:
            raise ValueError(
                "Unresolved references found in stitch file. "
                "The build will continue, but some cross-product links may be broken. "
                "Check the logs above for specific reference failures."
            )

    return etree.ElementTree(docservconfig)
