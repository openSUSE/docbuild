"""Tests for the LLMs integration module."""

from pathlib import Path

from justhtml import JustHTML

from docbuild.tasks.build.llms import (
    AntoraHTMLCleaner,
    DocBookHTMLCleaner,
    inject_llms_links,
)

DATA_DIR = Path(__file__).parent / "data"

def test_clean_and_convert_daps_article() -> None:
    """Ensure DAPS article HTML correctly strips navbars and side-tocs from the DOM."""
    daps_html = (DATA_DIR / "daps_article.html").read_text(encoding="utf-8")
    doc = JustHTML(daps_html, sanitize=False)

    cleaner = DocBookHTMLCleaner()
    cleaner.clean(doc.root)

    # Assert unwanted DOM nodes have been stripped completely
    assert not doc.query("nav")
    assert not doc.query("header")
    assert not doc.query("footer")
    assert not doc.query("aside")

def test_clean_and_convert_daps_book() -> None:
    """Ensure DAPS book HTML correctly strips navbars and side-tocs from the DOM."""
    daps_html = (DATA_DIR / "daps_book.html").read_text(encoding="utf-8")
    doc = JustHTML(daps_html, sanitize=False)

    cleaner = DocBookHTMLCleaner()
    cleaner.clean(doc.root)

    # Assert unwanted DOM nodes have been stripped completely
    assert not doc.query("nav")
    assert not doc.query("header")
    assert not doc.query("footer")
    assert not doc.query("aside")

def test_clean_and_convert_antora() -> None:
    """Ensure Antora HTML correctly strips toolbars and nav-containers from the DOM."""
    antora_html = (DATA_DIR / "antora_sample.html").read_text(encoding="utf-8")
    doc = JustHTML(antora_html, sanitize=False)

    cleaner = AntoraHTMLCleaner()
    cleaner.clean(doc.root)

    # Assert unwanted DOM nodes have been stripped completely
    assert not doc.query("nav")
    assert not doc.query("header")
    assert not doc.query("footer")
    assert not doc.query("aside")

def test_inject_llms_links_with_head() -> None:
    """Test link injection when <head> exists."""
    html = "<html><head><title>Test</title></head><body><h1>Hi</h1></body></html>"
    result = inject_llms_links(html, "docs/index.md", "llms.txt")
    assert '<link rel="alternate" type="text/markdown" href="docs/index.md">' in result
    assert '<link rel="alternate" type="text/markdown" href="llms.txt">' in result
    assert "<title>Test</title>" in result

def test_inject_llms_links_without_head() -> None:
    """Test link injection fallback when <head> is missing."""
    html = "<html><body><h1>No Head</h1></body></html>"
    result = inject_llms_links(html, "docs/index.md", "llms.txt")
    assert "<head>" in result
    assert '<link rel="alternate" type="text/markdown" href="docs/index.md">' in result
