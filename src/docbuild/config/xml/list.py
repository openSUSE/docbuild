"""List all deliverables from the stitched Docserv config."""

from collections.abc import Generator, Sequence
import logging

from lxml import etree

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
    # Select the product node regardless if its a child of "/" or under a
    # different root element.
    productnode = tree.xpath('(/product | /*/product)[1]')[0]
    # TODO: error handling if no product node is found?

    if doctypes is not None:
        log.debug('Filtering for docset %r', doctypes)
        for dt in doctypes:
            # Gradually build the XPath expression
            xpath = 'self::product'
            if '*' not in dt.product:
                xpath += f'[@productid={dt.product.value!r}]'

            xpath += '/docset'
            if '*' not in dt.docset:
                xpath += '[' + ' or '.join([f'@setid={d!r}' for d in dt.docset]) + ']'

            if LifecycleFlag.unknown != dt.lifecycle:  # type: ignore
                xpath += (
                    '['
                    + ' or '.join([f'@lifecycle={lc.name!r}' for lc in dt.lifecycle])
                    + ']'
                )

            xpath += '/builddocs/language'

            if '*' not in dt.langs:
                xpath += (
                    '['
                    + ' or '.join([f'@lang={lng.language!r}' for lng in dt.langs])
                    + ']'
                )

            xpath += '/deliverable'
            # -----------------
            # xpath = (
            #     f"/*/product[@productid={p!r}]"
            #     f"/docset"
            #     f"{xpath_lifecycle}"
            # )
            # if d not in (None, "*"):
            #     xpath += f"[@setid={d!r}]"
            # xpath += "/builddocs/language"
            # if lang is not None:
            #     xpath += f"[@lang={lang!r}]"
            # xpath += "/deliverable"
            # xpathlog.debug("XPath: %r", xpath)
            print('XPath:', xpath)
            nodes = productnode.xpath(xpath)
            if nodes:
                yield from nodes
            else:
                log.warning('No deliverables found for %r', dt)

    else:
        # TODO: do we need all languages? How to handle non-en-us languages?
        xpath = "self::product/docset/builddocs/language[@lang='en-us']/deliverable"
        xpathlog.debug('XPath: %r', xpath)
        print('XPath:', xpath)
        yield from productnode.xpath(xpath)
