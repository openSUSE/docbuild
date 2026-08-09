"""Tests for XML include resolution with source-path preservation."""

from pathlib import Path
from unittest.mock import MagicMock

from lxml import etree
import pytest

from docbuild.config.xml.xinclude import (
    XINCLUDE_NS,
    as_relative_posix,
    parse_xml_with_xinclude_base,
    replace_include_with_nodes,
    resolve_includes,
    xpointer_to_xpath,
)

XML_BASE_ATTR = "{http://www.w3.org/XML/1998/namespace}base"


def test_parse_xml_with_xinclude_base_nested_include_marks_source(tmp_path: Path) -> None:
    """Nested include target is tagged with path relative to root config file."""
    (tmp_path / "portal.xml").write_text(
        """
        <portal xmlns:xi="http://www.w3.org/2001/XInclude">
          <xi:include href="sles/sles.xml"/>
        </portal>
        """,
        encoding="utf-8",
    )
    (tmp_path / "sles").mkdir()
    (tmp_path / "sles" / "sles.xml").write_text(
        """
        <product xmlns:xi="http://www.w3.org/2001/XInclude">
          <xi:include href="16.0.xml"/>
        </product>
        """,
        encoding="utf-8",
    )
    (tmp_path / "sles" / "16.0.xml").write_text(
        """
        <docset id="sles.16.0" lifecycle="supported">
          <version>16.0</version>
        </docset>
        """,
        encoding="utf-8",
    )

    tree = parse_xml_with_xinclude_base(tmp_path / "portal.xml")

    docset = tree.xpath("//docset")
    assert len(docset) == 1
    assert docset[0].get(XML_BASE_ATTR) == "sles/16.0.xml"


def test_parse_xml_with_xinclude_base_supports_simple_xpointer(tmp_path: Path) -> None:
    """xpointer(/*/*) includes selected child nodes and marks their source."""
    (tmp_path / "portal.xml").write_text(
        """
        <portal xmlns:xi="http://www.w3.org/2001/XInclude">
          <xi:include href="categories.xml" xpointer="xpointer(/*/*)"/>
        </portal>
        """,
        encoding="utf-8",
    )
    (tmp_path / "categories.xml").write_text(
        """
        <categories>
          <category id="core"/>
        </categories>
        """,
        encoding="utf-8",
    )

    tree = parse_xml_with_xinclude_base(tmp_path / "portal.xml")

    category = tree.xpath("//category")
    assert len(category) == 1
    assert category[0].get(XML_BASE_ATTR) == "categories.xml"


def test_as_relative_posix_returns_absolute_when_outside_root(tmp_path: Path) -> None:
    """Path outside the root directory falls back to the absolute path."""
    outside = tmp_path / ".." / "outside.xml"

    result = as_relative_posix(outside, tmp_path)

    assert result == outside.resolve().as_posix()


def test_xpointer_to_xpath_rejects_unsupported_syntax() -> None:
    """Non-xpointer expressions yield no XPath."""
    assert xpointer_to_xpath("//category") is None
    assert xpointer_to_xpath("xpointer(/*") is None


def test_replace_include_with_nodes_root_single_node(tmp_path: Path) -> None:
    """A root-level include replaced by a single node is accepted."""
    (tmp_path / "include.xml").write_text(
        f'<xi:include xmlns:xi="{XINCLUDE_NS}" href="target.xml"/>',
        encoding="utf-8",
    )
    tree = etree.parse(str(tmp_path / "include.xml"))
    replacement = etree.fromstring("<replacement/>")

    replace_include_with_nodes(tree.getroot(), [replacement])


def test_replace_include_with_nodes_root_multiple_nodes_raises(tmp_path: Path) -> None:
    """A root-level include resolving to multiple nodes is rejected."""
    (tmp_path / "include.xml").write_text(
        f'<xi:include xmlns:xi="{XINCLUDE_NS}" href="target.xml"/>',
        encoding="utf-8",
    )
    tree = etree.parse(str(tmp_path / "include.xml"))
    nodes = [etree.fromstring("<a/>"), etree.fromstring("<b/>")]

    with pytest.raises(ValueError, match="exactly one element"):
        replace_include_with_nodes(tree.getroot(), nodes)


def test_parse_xml_include_without_tail(tmp_path: Path) -> None:
    """An include element with no trailing text is replaced cleanly."""
    (tmp_path / "portal.xml").write_text(
        f"""
        <portal xmlns:xi="{XINCLUDE_NS}">
          <section><xi:include href="part.xml"/></section>
        </portal>
        """,
        encoding="utf-8",
    )
    (tmp_path / "part.xml").write_text("<part id='p'/>", encoding="utf-8")

    tree = parse_xml_with_xinclude_base(tmp_path / "portal.xml")

    assert len(tree.xpath("//part")) == 1


def test_parse_xml_include_without_href_raises(tmp_path: Path) -> None:
    """An xi:include without href is rejected."""
    (tmp_path / "portal.xml").write_text(
        f'<portal xmlns:xi="{XINCLUDE_NS}"><xi:include/></portal>',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="without href"):
        parse_xml_with_xinclude_base(tmp_path / "portal.xml")


def test_parse_xml_include_unsupported_parse_mode_raises(tmp_path: Path) -> None:
    """Only the XML parse mode is supported."""
    (tmp_path / "portal.xml").write_text(
        f'<portal xmlns:xi="{XINCLUDE_NS}"><xi:include href="part.xml" parse="text"/></portal>',
        encoding="utf-8",
    )
    (tmp_path / "part.xml").write_text("plain text", encoding="utf-8")

    with pytest.raises(ValueError, match="parse mode"):
        parse_xml_with_xinclude_base(tmp_path / "portal.xml")


def test_parse_xml_recursive_include_raises(tmp_path: Path) -> None:
    """Recursive includes are detected and rejected."""
    (tmp_path / "portal.xml").write_text(
        f'<portal xmlns:xi="{XINCLUDE_NS}"><xi:include href="a.xml"/></portal>',
        encoding="utf-8",
    )
    (tmp_path / "a.xml").write_text(
        f'<a xmlns:xi="{XINCLUDE_NS}"><xi:include href="portal.xml"/></a>',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Recursive xi:include"):
        parse_xml_with_xinclude_base(tmp_path / "portal.xml")


def test_parse_xml_include_invalid_xpointer_raises(tmp_path: Path) -> None:
    """A non-xpointer xpointer attribute is rejected."""
    (tmp_path / "portal.xml").write_text(
        f'<portal xmlns:xi="{XINCLUDE_NS}"><xi:include href="part.xml" xpointer="bogus"/></portal>',
        encoding="utf-8",
    )
    (tmp_path / "part.xml").write_text("<part/>", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported xi:include xpointer"):
        parse_xml_with_xinclude_base(tmp_path / "portal.xml")


def test_parse_xml_include_xpointer_no_elements_raises(tmp_path: Path) -> None:
    """An xpointer selecting no elements is rejected."""
    (tmp_path / "portal.xml").write_text(
        f'<portal xmlns:xi="{XINCLUDE_NS}"><xi:include href="part.xml" xpointer="xpointer(/missing)"/></portal>',
        encoding="utf-8",
    )
    (tmp_path / "part.xml").write_text("<part><child/></part>", encoding="utf-8")

    with pytest.raises(ValueError, match="selected no elements"):
        parse_xml_with_xinclude_base(tmp_path / "portal.xml")


def test_resolve_includes_skips_non_element_nodes() -> None:
    """Non-element entries in the xinclude result list are ignored."""
    tree = MagicMock()
    tree.getroot.return_value.xpath.return_value = ["not-an-element"]

    resolve_includes(
        tree,
        current_path=Path("/tmp/portal.xml"),
        root_dir=Path("/tmp"),
        active_stack={Path("/tmp/portal.xml")},
    )

    tree.getroot.return_value.xpath.assert_called_once()
