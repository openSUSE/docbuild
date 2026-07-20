"""Deliverable discovery helpers for metadata-oriented task flows."""

from collections.abc import Iterator, Sequence

from lxml import etree

from ...models.deliverable import Deliverable
from ...models.doctype import Doctype


def get_deliverables_for_doctype(
    root: etree._ElementTree,
    doctype: Doctype,
) -> Iterator[Deliverable]:
    """Return DC deliverables that match a single doctype.

    :param root: Parsed portal XML tree with stitched configuration.
    :param doctype: Doctype selector provided by the user.
    :return: Iterator of DC deliverables matching the selector.
    """
    languages = root.getroot().xpath(doctype.xpath())
    for language in languages:
        for node in language.findall("deliverable"):
            deliverable = Deliverable(node)
            if deliverable.xml.is_dc:
                yield deliverable


def iter_doctype_groups(
    root: etree._ElementTree,
    doctypes: Sequence[Doctype],
) -> Iterator[tuple[str, str, list[Deliverable]]]:
    """Yield product and docset groups for each requested doctype.

    :param root: Parsed portal XML tree with stitched configuration.
    :param doctypes: Doctype selectors provided by the user.
    :yield: Tuples of product, docset, and grouped deliverables.
    """
    for doctype in doctypes:
        grouped: dict[tuple[str, str], list[Deliverable]] = {}
        for deliverable in get_deliverables_for_doctype(root, doctype):
            key = (deliverable.xml.productid, deliverable.xml.docsetid)
            grouped.setdefault(key, []).append(deliverable)

        for (product, docset), grouped_deliverables in grouped.items():
            yield product, docset, grouped_deliverables
