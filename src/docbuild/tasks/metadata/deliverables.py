"""Deliverable collection helpers for metadata processing."""

from collections.abc import Iterator
import logging

from lxml import etree

from docbuild.constants import DEFAULT_LANGS, XML_ID
from docbuild.models.deliverable import Deliverable
from docbuild.models.doctype import Doctype

log = logging.getLogger(__name__)


def get_deliverable_from_doctype(
    root: etree._ElementTree,
    doctype: Doctype,
) -> Iterator[Deliverable]:
    """Get deliverable from doctype.

    Each locale that defines ``<deliverable>`` elements uses its own list. A
    non-default locale without any inherits the default-language blueprint
    instead. Inherited entries are added to the locale element in ``root`` as
    synthetic ``<deliverable>`` nodes, which is a side effect on ``root``.

    :param root: The stitched XML node containing configuration.
    :param doctype: The Doctype object to process.
    :return: A list of deliverables for the given doctype.
    """
    languages = root.getroot().xpath(f"./{doctype.xpath()}")

    for language in languages:
        nodes = language.findall("deliverable")
        if nodes:
            yield from (Deliverable(node) for node in nodes)
        elif not is_default_lang(language):
            yield from inherit_default_blueprint(language)


def is_default_lang(language: etree._Element) -> bool:
    """Return True if the locale element is for a default language."""
    return language.attrib.get("lang") in DEFAULT_LANGS


def inherit_default_blueprint(language: etree._Element) -> Iterator[Deliverable]:
    """Create deliverables for ``language`` from the default-language blueprint.

    Each blueprint deliverable becomes a synthetic ``<deliverable>`` with an
    ``<xref>`` to it, appended to ``language`` so that the docset and product
    ancestors resolve.

    :param language: The non-default locale element with no deliverables.
    :return: The synthetic deliverables, or an empty list if there is no blueprint.
    """
    lang_code = language.get("lang")
    default_lang = DEFAULT_LANGS[0]
    default_locale = language.getparent().find(f"locale[@lang='{default_lang}']")
    if default_locale is None:
        return

    for blueprint in default_locale.findall("deliverable"):
        blueprint_id = blueprint.get(XML_ID)
        if not blueprint_id:
            log.warning("Skipping blueprint deliverable without xml:id")
            continue

        synth_node = etree.Element("deliverable")
        synth_node.append(etree.Element("xref", linkend=blueprint_id))
        language.append(synth_node)

        log.info(
            "Inherited blueprint deliverable '%s' for empty locale '%s'",
            blueprint_id,
            lang_code,
        )
        yield Deliverable(synth_node)
