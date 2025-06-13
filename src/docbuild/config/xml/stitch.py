"""Stitch file handling."""

import asyncio
from collections import Counter
from collections.abc import Callable, Sequence
from copy import deepcopy
import importlib
import inspect
import os
from pathlib import Path

from lxml import etree

from ...constants import XMLDATADIR


def load_check_functions() -> list[Callable]:
    """Load all check functions from :mod:`docbuild.config.xml.checks`."""
    xmlchecks = importlib.import_module('docbuild.config.xml.checks')

    return [
        func
        for name, func in inspect.getmembers(xmlchecks, inspect.isfunction)
        if name.startswith('check_')
    ]


# def log_memory_usage():
#     import psutil
#     process = psutil.Process(os.getpid())
#     print(f'Memory usage: {process.memory_info().rss / 1024**2:.2f} MB')


async def create_stitchfile(
    xmlfiles: Sequence[str | Path],
    *,
    xmlparser: etree.XMLParser | None = None,
) -> etree._ElementTree:
    """Asynchronously create a stitch file from a list of XML files.

    :param xmlfiles: A sequence of XML file paths to stitch together.
    :param xmlparser: An optional XML parser to use.
    :return: all XML file stitched together into a
        :class:`lxml.etree.ElementTree` object.
    """
    # TODO: Should we retrieve them from the config file?
    simplify_xslt = XMLDATADIR / 'simplify.xsl'
    reference_xslt = XMLDATADIR / 'global-check-ref-list.xsl'

    # TODO: Do we need the MD5 hashes? If so maybe store them

    async def parse_and_xinclude(file_path: Path) -> etree._ElementTree:
        """Parse a single XML file and run XInclude in a thread."""
        tree = await asyncio.to_thread(etree.parse, file_path, xmlparser)
        await asyncio.to_thread(tree.xinclude)
        return tree

    # Step 1: Concurrently parse all XML files
    docservconfig = etree.Element('docservconfig', attrib=None, nsmap=None)
    tasks = [parse_and_xinclude(Path(xmlfile)) for xmlfile in xmlfiles]
    parsed_trees = await asyncio.gather(*tasks)

    for tree in parsed_trees:
        # The deepcopy is unfortunately necessary to avoid
        # the "free(): invalid pointer" error
        docservconfig.append(deepcopy(tree.getroot()))
        del tree  # Explicitly delete the tree to free memory

    # log_memory_usage()

    # Step 2: Check for unique IDs
    product_ids = docservconfig.xpath('//@productid')
    if len(product_ids) > len(set(product_ids)):
        duplicates = [item for item, count in Counter(product_ids).items() if count > 1]
        raise ValueError(f'Duplicate product IDs found: {", ".join(duplicates)}')

    # Step 3: Check references

    return etree.ElementTree(docservconfig)
