"""Deliverable collection helpers for metadata processing."""

import logging

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

