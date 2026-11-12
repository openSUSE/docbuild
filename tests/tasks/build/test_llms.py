"""Tests for the LLMs integration module."""

from pathlib import Path
import re

from justhtml import JustHTML
from justhtml.dom import Element, Text
import pytest

from docbuild.tasks.build.llms import (
    AntoraHTMLCleaner,
    DocBookHTMLCleaner,
    HTMLCleaner,
    clean_and_convert,
    detect_generator,
    get_attrs,
    get_classes,
    get_cleaner,
    inject_llms_links,
    replace_node,
)

DATA_DIR = Path(__file__).parent / "data"


def test_clean_and_convert_daps_article() -> None:
    """Ensure DAPS article HTML strips navbars and converts tables cleanly."""
    daps_html = (DATA_DIR / "daps_article.html").read_text(encoding="utf-8")
    doc = JustHTML(daps_html, sanitize=False)

    cleaner = DocBookHTMLCleaner()
    cleaner.clean(doc.root)

    assert not doc.query("nav")
    assert not doc.query("header")
    assert not doc.query("footer")
    assert not doc.query("aside")

    md = clean_and_convert(daps_html)
    assert "<table" not in md
    assert "<img" not in md
    assert "| Attribute | Meaning | Value |" in md
    assert "| `NAME` | Full name of the distribution | SLES |" in md
    assert not re.findall(r"^\s*-\s*$", md, re.M)


def test_clean_and_convert_daps_book() -> None:
    """Ensure DAPS book HTML converts images, tables, and list items cleanly."""
    daps_html = (DATA_DIR / "daps_book.html").read_text(encoding="utf-8")
    doc = JustHTML(daps_html, sanitize=False)

    cleaner = DocBookHTMLCleaner()
    cleaner.clean(doc.root)

    assert not doc.query("nav")
    assert not doc.query("header")
    assert not doc.query("footer")
    assert not doc.query("aside")

    md = clean_and_convert(daps_html)
    assert "<table" not in md
    assert "<img" not in md
    assert (
        "![The Boot Screen on Machines with a Traditional BIOS]"
        "(images/install_boot.png)" in md
    )
    assert not re.findall(r"^\s*-\s*$", md, re.M)


def test_clean_and_convert_antora() -> None:
    """Ensure Antora HTML strips toolbars, anchors, and converts admonitions."""
    antora_html = (DATA_DIR / "antora_sample.html").read_text(encoding="utf-8")
    doc = JustHTML(antora_html, sanitize=False)

    cleaner = AntoraHTMLCleaner()
    cleaner.clean(doc.root)

    assert not doc.query("nav")
    assert not doc.query("header")
    assert not doc.query("footer")
    assert not doc.query("aside")

    md = clean_and_convert(antora_html)
    assert "<table" not in md
    assert "[](#" not in md
    assert "> **Warning:** After you set the Rancher Server URL" in md
    assert not re.findall(r"^\s*-\s*$", md, re.M)


def test_heading_number_spacing_and_admonition_fallbacks() -> None:
    """Ensure glued heading numbers, list divs, and admonition fallbacks work."""
    html = """<!DOCTYPE html>
<html>
<head><meta name="generator" content="DAPS 4.0"></head>
<body>
  <h2><span class="title-number">1</span><span class="title-name">What is node fencing?</span></h2>
  <ul>
    <li>   </li>
    <li><div class="paragraph"><p>Nested paragraph item</p></div></li>
  </ul>
  <div class="admonitionblock caution">
    <table><tr><td class="icon"><div class="title">Caution</div></td><td class="content">Plain text content</td></tr></table>
  </div>
  <div class="admonitionblock important">
    <table><tr><td class="icon"></td><td class="content"><p>Important text</p></td></tr></table>
  </div>
  <div class="admonitionblock"></div>
  <table></table>
  <img alt="no-src">
  <table><tr><td>A | B</td><td><img src="img/figure 1.png" alt="icon"></td></tr><tr><td>Only1</td></tr></table>
</body>
</html>"""
    md = clean_and_convert(html)
    assert "## 1 What is node fencing?" in md
    assert "- Nested paragraph item" in md
    assert "> **Caution:**" in md
    assert "> **Important:** Important text" in md
    assert "|  |  |" in md
    assert r"| A \| B | ![icon](img/figure%201.png) |" in md
    assert "| Only1 |  |" in md


def test_helper_edge_cases() -> None:
    """Test attribute extraction and node replacement edge cases."""
    assert get_attrs(Text("text")) == {}
    assert get_attrs(Element("div", None, "html")) == {}
    assert get_attrs(Element("div", {"id": "main", "disabled": None}, "html")) == {
        "id": "main",
        "disabled": "",
    }
    assert get_classes(Element("div", {"class": "one two"}, "html")) == ["one", "two"]
    cleaner = HTMLCleaner(
        tags_to_strip=["div"], ids_to_strip=None, classes_to_strip=None
    )
    assert not cleaner.should_strip(Text("text"))
    replace_node(Text("orphan"), None)


def test_replace_node_updates_parent_links() -> None:
    """Test replace_node updates parent and children links on replace and remove."""
    parent = Element("div", {}, "html")
    original = Element("span", {}, "html")
    parent.append_child(original)

    replacement = Text("replacement")
    replace_node(original, replacement)

    assert parent.children == [replacement]
    assert original.parent is None
    assert replacement.parent is parent

    replace_node(replacement, None)

    assert parent.children == []
    assert replacement.parent is None


def test_inject_llms_links_with_head() -> None:
    """Test link injection when <head> exists."""
    html = "<html><head><title>Test</title></head><body><h1>Hi</h1></body></html>"
    result = inject_llms_links(html, "docs/index.md", "llms.txt")
    assert '<link rel="alternate" type="text/markdown" href="docs/index.md">' in result
    assert '<link rel="alternate" type="text/markdown" href="llms.txt">' in result
    assert "<title>Test</title>" in result


def test_inject_llms_links_without_head(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test link injection fallback when <head> is missing from DOM."""
    orig_query_one = JustHTML.query_one
    monkeypatch.setattr(
        JustHTML,
        "query_one",
        lambda self, sel: None if sel == "head" else orig_query_one(self, sel),
    )
    html = "<html><body><h1>No Head</h1></body></html>"
    result = inject_llms_links(html, "docs/index.md", "llms.txt")
    assert "<head>" in result
    assert '<link rel="alternate" type="text/markdown" href="docs/index.md">' in result


def test_detect_generator_daps() -> None:
    """Test detect_generator identifies DAPS/DocBook generator meta tags."""
    doc = JustHTML(
        '<html><head><meta name="generator" content="DAPS 3.3.0"></head></html>',
        sanitize=False,
    )
    assert detect_generator(doc) == "daps"


def test_detect_generator_antora() -> None:
    """Test detect_generator identifies Antora generator meta tags."""
    doc = JustHTML(
        '<html><head><meta name="generator" content="Antora 3.1"></head></html>',
        sanitize=False,
    )
    assert detect_generator(doc) == "antora"


def test_detect_generator_unknown() -> None:
    """Test detect_generator returns None for unknown generators."""
    doc = JustHTML(
        '<html><head><meta name="generator" content="Custom Generator"></head></html>',
        sanitize=False,
    )
    assert detect_generator(doc) is None


def test_get_cleaner_fallback() -> None:
    """Test get_cleaner falls back to base HTMLCleaner for unknown generator."""
    doc = JustHTML("<p>Plain HTML</p>")
    cleaner = get_cleaner(doc)
    assert isinstance(cleaner, HTMLCleaner)


def test_clean_and_convert_full_flow() -> None:
    """Test end-to-end clean_and_convert output string."""
    html = """<!DOCTYPE html>
<html>
<head><meta name="generator" content="Antora 3.1"></head>
<body>
    <div class="toolbar">Toolbar</div>
    <main><h1>Title</h1><p>Body paragraph.</p></main>
</body>
</html>"""
    md = clean_and_convert(html)
    assert "Title" in md
    assert "Body paragraph." in md
    assert "Toolbar" not in md
