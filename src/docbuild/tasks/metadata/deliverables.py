"""Deliverable collection helpers for metadata processing."""

from collections.abc import Generator, Sequence
import logging
from pathlib import Path
from typing import Any

from lxml import etree

from docbuild.models.deliverable import Deliverable
from docbuild.models.doctype import Doctype

log = logging.getLogger(__name__)


def get_deliverable_from_doctype(
    root: etree._ElementTree,
    doctype: Doctype,
) -> list[Deliverable]:
    """Get deliverable from doctype.

    :param root: The stitched XML node containing configuration.
    :param doctype: The Doctype object to process.
    :return: A list of deliverables for the given doctype.
    """
    languages = root.getroot().xpath(f"./{doctype.xpath()}")

    return [
        Deliverable(node)
        for language in languages
        for node in language.findall("deliverable")
    ]


def collect_files_flat(
    doctypes: Sequence[Doctype],
    basedir: Path | str,
) -> Generator[tuple[Doctype, str, list[Path]], Any, None]:
    """Recursively collect all DC-metadata files from the cache directory.

    :param doctypes: Sequence of Doctype objects to filter by.
    :param basedir: The base directory to start the recursive search.
    :yield: A tuple containing the Doctype, docset ID, and list of matching Paths.
    """
    basedir = Path(basedir)
    task_stream = ((dt, ds) for dt in doctypes for ds in dt.docset)

    for dt, docset in task_stream:
        all_files = list(basedir.rglob("DC-*"))

        # Case-insensitive filtering
        files = [
            f for f in all_files
            if dt.product.acronym.lower() in [p.lower() for p in f.parts]
            and docset.lower() in [p.lower() for p in f.parts]
        ]

        if files:
            yield dt, docset, files
