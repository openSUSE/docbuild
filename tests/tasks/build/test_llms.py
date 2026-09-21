from docbuild.tasks.build.llms import HTMLStripper, clean_and_convert, inject_llms_links


def test_html_stripper_basic() -> None:
    html = '<html><body><p id="main">Test</p></body></html>'
    stripper = HTMLStripper([], [], [])
    stripper.feed(html)
    assert stripper.get_clean_html() == html


def test_html_stripper_removes_tags() -> None:
    html = '<body><nav>Skip this</nav><p>Keep this</p></body>'
    stripper = HTMLStripper(["nav"], [], [])
    stripper.feed(html)
    assert stripper.get_clean_html() == '<body><p>Keep this</p></body>'


def test_html_stripper_removes_ids_and_classes() -> None:
    html = '<div id="toc">TOC</div><div class="navbar">Nav</div><p class="keep">Text</p>'
    stripper = HTMLStripper([], ["toc"], ["navbar"])
    stripper.feed(html)
    assert stripper.get_clean_html() == '<p class="keep">Text</p>'


def test_html_stripper_nested_stripping() -> None:
    html = '<header><div><p>Deep skip</p></div></header><main>Content</main>'
    stripper = HTMLStripper(["header"], [], [])
    stripper.feed(html)
    assert stripper.get_clean_html() == '<main>Content</main>'


def test_html_stripper_void_elements() -> None:
    html = '<div><img src="test.png"><hr></div><meta class="toc">'
    stripper = HTMLStripper([], [], ["toc"])
    stripper.feed(html)
    assert stripper.get_clean_html() == '<div><img src="test.png"><hr></div>'


def test_html_stripper_entities_and_comments() -> None:
    html = '<div>&amp; &#160; <!-- comment --> <!DOCTYPE html></div><nav>&amp;</nav>'
    stripper = HTMLStripper(["nav"], [], [])
    stripper.feed(html)
    assert stripper.get_clean_html() == '<div>&amp; &#160; <!-- comment --> <!DOCTYPE html></div>'


def test_html_stripper_startendtag() -> None:
    html = '<img src="a.jpg" /><img class="navbar" src="b.jpg" />'
    stripper = HTMLStripper([], [], ["navbar"])
    stripper.feed(html)
    assert stripper.get_clean_html() == '<img src="a.jpg" />'


def test_clean_and_convert() -> None:
    raw_html = """
    <html>
    <head><title>Test</title></head>
    <body>
        <header>My Header</header>
        <nav id="_mainnav">Nav items</nav>
        <div id="toc">Table of contents</div>
        <main>
            <h1>Main Title</h1>
            <p>Important text.</p>
            <a class="permalink" href="#main">#</a>
        </main>
        <footer>My Footer</footer>
    </body>
    </html>
    """
    markdown = clean_and_convert(raw_html)
    assert "Main Title" in markdown
    assert "Important text." in markdown

    # Assert stripped items are GONE
    assert "My Header" not in markdown
    assert "Nav items" not in markdown
    assert "Table of contents" not in markdown
    assert "My Footer" not in markdown


def test_inject_llms_links_with_head() -> None:
    html = "<html><head><title>T</title></head><body></body></html>"
    result = inject_llms_links(html, "doc.md", "llms.txt")
    assert '<link rel="alternate" type="text/markdown" href="doc.md">' in result
    assert '<link rel="alternate" type="text/markdown" href="llms.txt">' in result
    assert "</head>" in result


def test_inject_llms_links_without_head() -> None:
    html = "<html><body>No head here</body></html>"
    result = inject_llms_links(html, "doc.md", "llms.txt")
    assert result == html  # Should return unmodified safely
