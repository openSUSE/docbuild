"""List all deliverables from the stitched Docserv config."""

from collections.abc import Generator, Sequence
import logging

from lxml import etree  # type: ignore

from ...models.doctype import Doctype

xpathlog = logging.getLogger(__name__)
log = logging.getLogger(__package__)


def list_all_deliverables(
    tree: etree._Element | etree._ElementTree,
    doctypes: Sequence[Doctype] | None = None,
) -> Generator[etree._Element, None, None]:
    """Generate to list all deliverables from the stitched Docserv config.

    :param tree: the XML tree from the stitched Docserv config
    :param doctypes: a sequence of :class:`~docbuild.models.doctype.Doctype` objects.
    :yield: the ``<deliverable>`` node that matches the criteria
    """
    if doctypes is not None:
        log.debug("Filtering for docset %r", doctypes)
        for dt in doctypes:
            xpath = f"{dt.xpath(absolute=True)}/deliverable"
            nodes = tree.xpath(xpath)
            if nodes:
                yield from nodes
            else:
                log.warning("No deliverables found for %r", dt)

    else:
        # Default fallback route with a flexible relative search path pattern
        dt = Doctype.from_str("//en-us")
        xpath = f"{dt.xpath(absolute=True)}/deliverable"

        xpathlog.debug("XPath: %r", xpath)
        yield from tree.xpath(xpath)
