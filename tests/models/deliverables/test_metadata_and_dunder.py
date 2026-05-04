"""Metadata and dunder behavior tests for deliverables."""

import pytest

from docbuild.models.deliverable import Deliverable
from docbuild.models.metadata import Metadata


def test_metafile_setter(first_deliverable: Deliverable) -> None:
    assert first_deliverable.metafile is None
    first_deliverable.metafile = "meta.xml"
    assert first_deliverable.metafile == "meta.xml"


def test_meta_default(first_deliverable: Deliverable) -> None:
    assert first_deliverable.meta is None


def test_meta_setter_type_check(first_deliverable: Deliverable) -> None:
    with pytest.raises(TypeError, match="Expected Metadata"):
        first_deliverable.meta = "wrong-type"


def test_meta_setter(first_deliverable: Deliverable) -> None:
    metadata = Metadata(rootid="foo")
    first_deliverable.meta = metadata
    assert first_deliverable.meta is metadata


def test_hash_uses_full_id(first_deliverable: Deliverable) -> None:
    assert hash(first_deliverable) == hash(first_deliverable.full_id)


def test_repr_contains_product_and_docset(first_deliverable: Deliverable) -> None:
    representation = repr(first_deliverable)
    assert "Deliverable(" in representation
    assert "productid='sles'" in representation
    assert "docsetid='15-SP6'" in representation


def test_make_safe_name() -> None:
    assert (
        Deliverable.make_safe_name("maintenance/SLE15:SP6")
        == "maintenance_SLE15-SP6"
    )


def test_xml_str_representation(first_deliverable: Deliverable) -> None:
    """Test the __str__ method of DeliverableXMLView."""
    xml_str = str(first_deliverable.xml)
    assert "productid='sles'" in xml_str
    assert "docsetid='15-SP6'" in xml_str
    assert "lang=" in xml_str
    assert "branch=" in xml_str
    assert "dcfile=" in xml_str


def test_xml_repr(first_deliverable: Deliverable) -> None:
    """Test the __repr__ method of DeliverableXMLView."""
    xml_repr = repr(first_deliverable.xml)
    assert "DeliverableXMLView(" in xml_repr
