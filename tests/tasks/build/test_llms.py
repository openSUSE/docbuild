"""Tests for the LLMs integration module."""

from pathlib import Path

from justhtml import JustHTML

from docbuild.tasks.build.llms import (
    AntoraHTMLCleaner,
    DocBookHTMLCleaner,
    HTMLCleaner,
    clean_and_convert,
    detect_generator,
    get_cleaner,
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


def test_detect_generator_daps() -> None:
    """Test detect_generator identifies DAPS/DocBook generator meta tags."""
    doc = JustHTML('<html><head><meta name="generator" content="DAPS 3.3.0"></head></html>', sanitize=False)
    assert detect_generator(doc) == "daps"


def test_detect_generator_antora() -> None:
    """Test detect_generator identifies Antora generator meta tags."""
    doc = JustHTML('<html><head><meta name="generator" content="Antora 3.1"></head></html>', sanitize=False)
    assert detect_generator(doc) == "antora"


def test_detect_generator_unknown() -> None:
    """Test detect_generator returns None for unknown generators."""
    doc = JustHTML('<html><head><meta name="generator" content="Custom Generator"></head></html>', sanitize=False)
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
