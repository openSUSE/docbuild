"""Unit tests for individual reference checking functions."""

from copy import deepcopy

from lxml import etree
import pytest

from docbuild.config.xml.references import (
    check_ref_to_deliverable,
    check_ref_to_docset,
    check_ref_to_link,
    check_ref_to_product,
    check_ref_to_subdeliverable,
    check_stitched_references,
)


@pytest.fixture
def xml_tree() -> etree._Element:
    """Provide a base XML tree for reference checking tests."""
    return etree.fromstring(
        """<docservconfig>
            <product productid="p1" schemaversion="6.0">
                <name>Product 1</name>
                <docset setid="ds1">
                    <builddocs>
                        <language lang="en-us" default="1">
                            <deliverable>
                                <dc>DC-1</dc>
                                <subdeliverable>sub-1</subdeliverable>
                            </deliverable>
                            <deliverable>
                                <dc>DC-2</dc>
                            </deliverable>
                            <external>
                                <link linkid="link-1">https://example.com</link>
                            </external>
                        </language>
                    </builddocs>
                    <internal>
                        <!-- Test refs will be added here -->
                    </internal>
                </docset>
                <docset setid="ds2">
                    <!-- Empty docset for testing -->
                </docset>
            </product>
            <product productid="p2">
                <!-- Empty product for testing -->
            </product>
        </docservconfig>"""
    )


def add_ref(tree: etree._Element, attrs: dict[str, str]) -> etree._Element:
    """Add a <ref> element to the test tree and return it."""
    internal_node = tree.find(".//internal")
    ref_element = etree.SubElement(internal_node, "ref", attrib=attrs)
    return ref_element


class TestCheckRefToSubdeliverable:
    def test_valid_ref(self, xml_tree):
        """Test a valid reference to a subdeliverable."""
        attrs = {
            "product": "p1",
            "docset": "ds1",
            "dc": "DC-1",
            "subdeliverable": "sub-1",
        }
        ref = add_ref(xml_tree, attrs)
        assert check_ref_to_subdeliverable(ref, attrs) is None

    def test_invalid_ref_does_not_exist(self, xml_tree):
        """Test an invalid reference to a non-existent subdeliverable."""
        attrs = {
            "product": "p1",
            "docset": "ds1",
            "dc": "DC-1",
            "subdeliverable": "invalid",
        }
        ref = add_ref(xml_tree, attrs)
        result = check_ref_to_subdeliverable(ref, attrs)
        assert result is not None
        assert "Referenced subdeliverable does not exist" in result


class TestCheckRefToDeliverable:
    def test_valid_ref(self, xml_tree):
        """Test a valid reference to a deliverable without subdeliverables."""
        attrs = {"product": "p1", "docset": "ds1", "dc": "DC-2"}
        ref = add_ref(xml_tree, attrs)
        assert check_ref_to_deliverable(ref, attrs) is None

    def test_invalid_ref_has_subdeliverables(self, xml_tree):
        """Test reference to a deliverable that has subdeliverables."""
        attrs = {"product": "p1", "docset": "ds1", "dc": "DC-1"}
        ref = add_ref(xml_tree, attrs)
        result = check_ref_to_deliverable(ref, attrs)
        assert result is not None
        assert "Referenced deliverable has subdeliverables" in result

    def test_invalid_ref_does_not_exist(self, xml_tree):
        """Test reference to a deliverable that does not exist."""
        attrs = {"product": "p1", "docset": "ds1", "dc": "invalid-dc"}
        ref = add_ref(xml_tree, attrs)
        result = check_ref_to_deliverable(ref, attrs)
        assert result is not None
        assert "Referenced deliverable does not exist" in result


class TestCheckRefToLink:
    def test_valid_ref(self, xml_tree):
        """Test a valid reference to an external link."""
        attrs = {"product": "p1", "docset": "ds1", "link": "link-1"}
        ref = add_ref(xml_tree, attrs)
        assert check_ref_to_link(ref, attrs) is None

    def test_invalid_ref_does_not_exist(self, xml_tree):
        """Test reference to a link that does not exist."""
        attrs = {"product": "p1", "docset": "ds1", "link": "invalid-link"}
        ref = add_ref(xml_tree, attrs)
        result = check_ref_to_link(ref, attrs)
        assert result is not None
        assert "Referenced external link does not exist" in result


class TestCheckRefToDocset:
    def test_valid_ref(self, xml_tree):
        """Test a valid reference to a docset."""
        attrs = {"product": "p1", "docset": "ds2"}
        ref = add_ref(xml_tree, attrs)
        assert check_ref_to_docset(ref, attrs) is None

    def test_invalid_ref_does_not_exist(self, xml_tree):
        """Test reference to a docset that does not exist."""
        attrs = {"product": "p1", "docset": "invalid-ds"}
        ref = add_ref(xml_tree, attrs)
        result = check_ref_to_docset(ref, attrs)
        assert result is not None
        assert "Referenced docset does not exist" in result


class TestCheckRefToProduct:
    def test_valid_ref(self, xml_tree):
        """Test a valid reference to a product."""
        attrs = {"product": "p2"}
        ref = add_ref(xml_tree, attrs)
        assert check_ref_to_product(ref, attrs) is None

    def test_invalid_ref_does_not_exist(self, xml_tree):
        """Test reference to a product that does not exist."""
        attrs = {"product": "invalid-p"}
        ref = add_ref(xml_tree, attrs)
        result = check_ref_to_product(ref, attrs)
        assert result is not None
        assert "Referenced product does not exist" in result


class TestCheckStitchedReferences:
    """Tests the main orchestrator function."""

    def test_all_valid_refs(self, xml_tree):
        """Test that no errors are returned for a file with all valid refs."""
        add_ref(
            xml_tree,
            {"product": "p1", "docset": "ds1", "dc": "DC-1", "subdeliverable": "sub-1"},
        )
        add_ref(xml_tree, {"product": "p1", "docset": "ds1", "dc": "DC-2"})
        add_ref(xml_tree, {"product": "p1", "docset": "ds1", "link": "link-1"})
        add_ref(xml_tree, {"product": "p1", "docset": "ds2"})
        add_ref(xml_tree, {"product": "p2"})

        errors = check_stitched_references(etree.ElementTree(xml_tree))
        assert not errors, f"Expected no errors, but got: {errors}"

    def test_all_invalid_refs(self, xml_tree):
        """Test that all invalid reference types are caught."""
        tree_copy = deepcopy(xml_tree)
        add_ref(
            tree_copy,
            {
                "product": "p1",
                "docset": "ds1",
                "dc": "DC-1",
                "subdeliverable": "invalid",
            },
        )
        add_ref(tree_copy, {"product": "p1", "docset": "ds1", "dc": "DC-1"})
        add_ref(tree_copy, {"product": "p1", "docset": "ds1", "dc": "invalid-dc"})
        add_ref(tree_copy, {"product": "p1", "docset": "ds1", "link": "invalid-link"})
        add_ref(tree_copy, {"product": "p1", "docset": "invalid-ds"})
        add_ref(tree_copy, {"product": "invalid-p"})

        errors = check_stitched_references(etree.ElementTree(tree_copy))
        assert len(errors) == 6

    def test_invalid_ref_element_structure(self, xml_tree):
        """Test a <ref> element with insufficient attributes."""
        add_ref(xml_tree, {})  # Empty ref
        errors = check_stitched_references(etree.ElementTree(xml_tree))
        assert len(errors) == 1
        assert "This is a docserv-stitch bug" in errors[0]
