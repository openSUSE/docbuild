"""List all deliverables from the stitched Docserv config."""

from collections.abc import Generator, Sequence
import logging

from lxml import etree  # type: ignore

from ...models.doctype import Doctype
from ...models.lifecycle import LifecycleFlag

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
            # Using flexible relative descendant selectors ensures compatibility
            # with both nested test fixtures and the absolute portal configuration schema.
            xpath = "//product"
            if dt.product and "*" not in dt.product:
                xpath += f"[@id={dt.product.value!r}]"

            xpath += "/docset"
            # Protect against empty lists causing malformed [] XPath segments
            if dt.docset and "*" not in dt.docset:
                xpath += "[" + " or ".join([f"@path={d!r}" for d in dt.docset]) + "]"

            if dt.lifecycle and LifecycleFlag.unknown != dt.lifecycle:  # type: ignore
                xpath += (
                    "["
                    + " or ".join([f"@lifecycle={lc.name!r}" for lc in dt.lifecycle])
                    + "]"
                )

            xpath += "/resources/locale"

            if dt.langs and "*" not in dt.langs:
                xpath += (
                    "["
                    + " or ".join([f"@lang={lng.language!r}" for lng in dt.langs])
                    + "]"
                )
            elif not dt.langs:
                # Toms' Suggestion: Fallback to English if no language is specified
                xpath += "[@lang='en-us']"

            xpath += "/deliverable"

            nodes = tree.xpath(xpath)
            if nodes:
                yield from nodes
            else:
                log.warning("No deliverables found for %r", dt)

    else:
        # Default fallback route with a flexible relative search path pattern
        xpath = "//product/docset/resources/locale[@lang='en-us']/deliverable"
        # if not tree.xpath(xpath):
        #    # Fallback alignment support variant for raw test fixtures
        #    xpath = "//product/docset/resources/locale[@lang='en-us']/deliverable"

        xpathlog.debug("XPath: %r", xpath)
        yield from tree.xpath(xpath)
