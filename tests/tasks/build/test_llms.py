"""Tests for the LLMs integration module."""

from docbuild.tasks.build.llms import clean_and_convert, inject_llms_links

DAPS_HTML = """
<html>
<head>
    <meta name="generator" content="DAPS">
    <title>SLES Guide</title>
</head>
<body>
    <div id="_mainnav" class="navbar">Menu</div>
    <aside id="_side-toc-page">TOC</aside>
    <main>
        <h1>Introduction</h1>
        <p>This is core content.</p>
        <a class="permalink" href="#intro">Link</a>
    </main>
    <footer class="bottom-pagination">Next Page</footer>
</body>
</html>
"""

ANTORA_HTML = """
<html>
<head>
    <meta name="generator" content="Antora">
    <title>Rancher Guide</title>
</head>
<body>
    <header class="toolbar">Top Nav</header>
    <nav class="nav-container">
        <div class="nav-panel-menu">Menu</div>
    </nav>
    <main>
        <h1>Concept</h1>
        <p>Rancher core concept.</p>
    </main>
    <footer class="footer">Copyright</footer>
</body>
</html>
"""

def test_clean_and_convert_daps() -> None:
    """Ensure DAPS HTML correctly strips navbars, side-tocs, and permalinks."""
    md = clean_and_convert(DAPS_HTML)
    assert "Introduction" in md
    assert "This is core content." in md
    assert "Menu" not in md
    assert "TOC" not in md
    assert "Link" not in md
    assert "Next Page" not in md

def test_clean_and_convert_antora() -> None:
    """Ensure Antora HTML correctly strips toolbars, nav-containers, and footers."""
    md = clean_and_convert(ANTORA_HTML)
    assert "Concept" in md
    assert "Rancher core concept." in md
    assert "Top Nav" not in md
    assert "Menu" not in md
    assert "Copyright" not in md

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
