"""Tests for the LLMs integration module."""

from pathlib import Path

from docbuild.tasks.build.llms import clean_and_convert, inject_llms_links

DATA_DIR = Path(__file__).parent / "data"

def test_clean_and_convert_daps() -> None:
    """Ensure DAPS HTML correctly strips navbars, side-tocs, and permalinks."""
    daps_html = (DATA_DIR / "daps_sample.html").read_text(encoding="utf-8")
    md = clean_and_convert(daps_html)

    assert "Introduction" in md
    assert "This is the core content that should remain." in md
    assert "Menu content" not in md
    assert "TOC content" not in md
    assert "Link" not in md
    assert "Next Page" not in md

def test_clean_and_convert_antora() -> None:
    """Ensure Antora HTML correctly strips toolbars, nav-containers, and footers."""
    antora_html = (DATA_DIR / "antora_sample.html").read_text(encoding="utf-8")
    md = clean_and_convert(antora_html)

    assert "Concept" in md
    assert "Rancher core concept that should remain." in md
    assert "Top Nav content" not in md
    assert "Menu content" not in md
    assert "Copyright 2026" not in md

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
