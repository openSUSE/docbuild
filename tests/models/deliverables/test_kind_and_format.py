"""Deliverable kind and format tests."""

from lxml import etree

from docbuild.models.deliverable import Deliverable


def test_dc_kind(first_deliverable: Deliverable) -> None:
    assert first_deliverable.xml.is_dc is True
    assert first_deliverable.xml.is_ref is False
    assert first_deliverable.xml.is_prebuilt is False


def test_ref_kind(first_ref_deliverable: Deliverable) -> None:
    assert first_ref_deliverable.xml.is_ref is True
    assert first_ref_deliverable.xml.is_dc is False


def test_prebuilt_kind(first_prebuilt_deliverable: Deliverable) -> None:
    assert first_prebuilt_deliverable.xml.is_prebuilt is True
    assert first_prebuilt_deliverable.xml.is_dc is False


def test_dc_format_attrs(first_deliverable: Deliverable) -> None:
    assert first_deliverable.xml.format_attrs() == {
        "epub": False,
        "html": False,
        "pdf": True,
        "single-html": True,
    }


def test_ref_format_attrs(first_ref_deliverable: Deliverable) -> None:
    assert first_ref_deliverable.xml.format_attrs() == {
        "epub": False,
        "html": True,
        "pdf": True,
        "single-html": True,
    }


def test_prebuilt_format_attrs(first_prebuilt_deliverable: Deliverable) -> None:
    assert first_prebuilt_deliverable.xml.format_attrs() == {
        "epub": False,
        "html": True,
        "pdf": False,
        "single-html": True,
    }


def test_kind_property_when_type_missing(node: etree._ElementTree) -> None:
    """Test that kind property returns None when @type is missing."""
    # Remove all @type attributes from deliverables
    for deli in node.xpath("//deliverable"):
        if "type" in deli.attrib:
            del deli.attrib["type"]

    first_node = node.xpath("(/product | /portal/product)/docset/resources/locale[@lang='en-us']/deliverable")[0]
    deliverable = Deliverable(first_node)
    assert deliverable.xml.kind is None


def test_fallback_is_dc_from_dcfile(node: etree._ElementTree) -> None:
    """Test that is_dc returns True based on dcfile when @type is missing."""
    # Remove all @type attributes
    for deli in node.xpath("//deliverable"):
        if "type" in deli.attrib:
            del deli.attrib["type"]

    first_node = node.xpath("(/product | /portal/product)/docset/resources/locale[@lang='en-us']/deliverable")[0]
    deliverable = Deliverable(first_node)
    assert deliverable.xml.is_dc is True
    assert deliverable.xml.is_ref is False
    assert deliverable.xml.is_prebuilt is False


def test_fallback_is_ref_from_child_tag(ref_node: etree._ElementTree) -> None:
    """Test that is_ref returns True based on <ref> child when @type is missing."""
    # Remove all @type attributes
    for deli in ref_node.xpath("//deliverable"):
        if "type" in deli.attrib:
            del deli.attrib["type"]

    first_node = ref_node.xpath("(/product | /portal/product)/docset/resources/locale[@lang='de-de']/deliverable")[0]
    deliverable = Deliverable(first_node)
    assert deliverable.xml.is_ref is True
    assert deliverable.xml.is_dc is False
    assert deliverable.xml.is_prebuilt is False


def test_fallback_is_prebuilt_from_child_tag(prebuilt_node: etree._ElementTree) -> None:
    """Test that is_prebuilt returns True based on <prebuilt> child when @type is missing."""
    # Remove all @type attributes
    for deli in prebuilt_node.xpath("//deliverable"):
        if "type" in deli.attrib:
            del deli.attrib["type"]

    first_node = prebuilt_node.xpath("(/product | /portal/product)/docset/resources/locale[@lang='en-us']/deliverable")[0]
    deliverable = Deliverable(first_node)
    assert deliverable.xml.is_prebuilt is True
    assert deliverable.xml.is_dc is False
    assert deliverable.xml.is_ref is False
