"""Shared fixtures for deliverable model tests."""

from collections.abc import Callable
from pathlib import Path

from lxml import etree
import pytest

from docbuild.models.deliverable import Deliverable
from docbuild.models.metadata import Metadata

#
DATADIR = Path(__file__).resolve().parent / "data"


def _parse_xml(xml_file: str) -> etree._ElementTree:
    root = etree.fromstring((DATADIR / xml_file).read_text(), parser=None)
    return root.getroottree()


def _first_deliverable_node(node: etree._ElementTree, *, lang: str) -> etree._Element:
    result = node.xpath(
        (
            "(/product | /portal/product)"
            f"/docset/resources/locale[@lang={lang!r}]/deliverable"
        ),
    )
    assert result
    return result[0]


@pytest.fixture
def node() -> etree._ElementTree:
    """Return a minimal XML tree for common deliverable tests."""
    return _parse_xml("minimal_dc.xml")


@pytest.fixture
def root_categories_node() -> etree._ElementTree:
    """Return an XML tree with product and root-level categories."""
    return _parse_xml("root_categories.xml")


@pytest.fixture
def ref_node() -> etree._ElementTree:
    """Return an XML tree with a translated reference deliverable."""
    return _parse_xml("ref_locale.xml")


@pytest.fixture
def prebuilt_node() -> etree._ElementTree:
    """Return an XML tree with one prebuilt deliverable."""
    return _parse_xml("prebuilt.xml")


@pytest.fixture
def first_deliverable(node: etree._ElementTree) -> Deliverable:
    """Return the first English deliverable model."""
    return Deliverable(_first_deliverable_node(node, lang="en-us"))


@pytest.fixture
def first_de_deliverable(node: etree._ElementTree) -> Deliverable:
    """Return the first German deliverable model."""
    return Deliverable(_first_deliverable_node(node, lang="de-de"))


@pytest.fixture
def first_ref_deliverable(ref_node: etree._ElementTree) -> Deliverable:
    """Return the first German reference deliverable model."""
    return Deliverable(_first_deliverable_node(ref_node, lang="de-de"))


@pytest.fixture
def first_prebuilt_deliverable(prebuilt_node: etree._ElementTree) -> Deliverable:
    """Return the first English prebuilt deliverable model."""
    return Deliverable(_first_deliverable_node(prebuilt_node, lang="en-us"))


@pytest.fixture
def first_deliverable_from_lang() -> Callable[[etree._ElementTree, str], Deliverable]:
    """Return a helper to build a first deliverable model for a language."""

    def _factory(xml_node: etree._ElementTree, lang: str) -> Deliverable:
        return Deliverable(_first_deliverable_node(xml_node, lang=lang))

    return _factory


@pytest.fixture
def meta_without_rootid() -> Metadata:
    """Return a predefined Metadata instance missing a rootid."""
    return Metadata(rootid=None)
