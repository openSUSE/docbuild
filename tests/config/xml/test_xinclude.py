"""Tests for XML include resolution with source-path preservation."""

from pathlib import Path

from docbuild.config.xml.xinclude import parse_xml_with_xinclude_base

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
