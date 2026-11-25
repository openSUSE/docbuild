"""Tests for the LLMs integration module."""

import json
from pathlib import Path
import re

from justhtml import JustHTML
from justhtml.dom import Element, Text
import pytest
import yaml

from docbuild.models.json_ld import JsonLDEntity, JsonLDImage
from docbuild.tasks.build.llms.cleaners import (
    AntoraHTMLCleaner,
    DocBookHTMLCleaner,
    HTMLCleaner,
)
from docbuild.tasks.build.llms.core import (
    clean_and_convert,
    detect_generator,
    get_cleaner,
    inject_llms_links,
)
from docbuild.tasks.build.llms.dom import (
    get_attrs,
    get_classes,
    replace_node,
)
from docbuild.tasks.build.llms.generator import (
    extract_json_ld,
    process_single_html_file,
)

DATA_DIR = Path(__file__).parent / "data"


def test_extract_json_ld_from_daps_article() -> None:
    """Extract typed nested metadata from the DAPS article fixture."""
    html_file = DATA_DIR / "daps_article.html"
    metadata = extract_json_ld(html_file.read_text(encoding="utf-8"), html_file)

    assert metadata is not None
    assert metadata.type == ["TechArticle"]
    assert metadata.name == "Identifying Operating Systems | SUSE Linux"
    assert isinstance(metadata.author, list)
    assert isinstance(metadata.author[0], JsonLDEntity)
    assert metadata.author[0].type == "Corporation"
    assert metadata.is_part_of is not None
    assert metadata.is_part_of.name == "Products &amp; Solutions"
    assert isinstance(metadata.mentions, list)
    assert metadata.mentions[0].operating_system == "Linux"
    assert metadata.publisher is not None
    assert isinstance(metadata.publisher.logo, JsonLDImage)
    assert metadata.publisher.logo.type == "ImageObject"
    assert metadata.date_published == "2026-09-17T07:21+02:00"


def test_extract_json_ld_from_antora_article() -> None:
    """Extract typed nested metadata from the Antora article fixture."""
    html_file = DATA_DIR / "antora_sample.html"
    metadata = extract_json_ld(html_file.read_text(encoding="utf-8"), html_file)

    assert metadata is not None
    assert metadata.type == "TechArticle"
    assert metadata.headline == "Authentication, Permissions and Global Settings"
    assert isinstance(metadata.author, JsonLDEntity)
    assert metadata.author.name == "SUSE Product & Solution Documentation Team"
    assert isinstance(metadata.mentions, list)
    assert metadata.mentions[0].software_version == "v2.15"
    assert metadata.mentions[0].application_category == "Cloud Infrastructure"
    assert metadata.publisher is not None
    assert isinstance(metadata.publisher.logo, JsonLDImage)
    assert metadata.publisher.logo.url == "https://www.suse.com/assets/img/suse-white-logo-green.svg"


def test_extract_json_ld_with_inline_context_and_image(tmp_path: Path) -> None:
    """Accept structured JSON-LD contexts and image objects."""
    payload = {
        "@context": {"@vocab": "https://schema.org/"},
        "image": {"@type": "ImageObject", "url": "https://example.com/image.jpg"},
    }
    html = f'<script type="application/ld+json">{json.dumps(payload)}</script>'

    metadata = extract_json_ld(html, tmp_path / "article.html")

    assert metadata is not None
    assert metadata.context == {"@vocab": "https://schema.org/"}
    assert isinstance(metadata.image, JsonLDImage)
    assert metadata.image.url == "https://example.com/image.jpg"


@pytest.mark.asyncio
async def test_json_ld_extensions_warn_and_do_not_expand_frontmatter(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Keep extensions while warning about their paths and limiting YAML fields."""
    html_file = tmp_path / "index.html"
    payload = {
        "name": "Article title",
        "description": "Article description",
        "dateCreated": "2026-01-02",
        "dateModified": "2026-02-03",
        "datePublished": "2026-03-04",
        "author": {"@type": "Organization", "name": "Docs team"},
        "mentions": [{"@type": "SoftwareApplication", "name": "Product"}],
        "publisher": {
            "@type": "Organization",
            "name": "Publisher",
            "logo": {"@type": "ImageObject", "urll": "https://example.com/logo"},
        },
        "descripton": "Extension value",
    }
    html = (
        '<html><head><script type="application/ld+json">'
        f'{json.dumps(payload)}</script></head><body><h1>Article</h1></body></html>'
    )
    html_file.write_text(html, encoding="utf-8")

    with caplog.at_level("WARNING", logger="docbuild.tasks.build.llms.generator"):
        metadata = extract_json_ld(html, html_file)
        await process_single_html_file(
            html_file, tmp_path, tmp_path / "docs", "docs", "guides", "Fallback",
            only_md=True,
        )

    assert metadata is not None
    dumped = metadata.model_dump(by_alias=True, exclude_none=True)
    assert dumped["descripton"] == "Extension value"
    assert dumped["publisher"]["logo"]["urll"] == "https://example.com/logo"
    markdown = (tmp_path / "docs/guides/index.md").read_text(encoding="utf-8")
    frontmatter = yaml.safe_load(markdown.split("---")[1])
    assert frontmatter == {
        "title": "Article title",
        "description": "Article description",
        "dateCreated": "2026-01-02",
        "dateModified": "2026-02-03",
        "datePublished": "2026-03-04",
    }
    warnings = [record.getMessage() for record in caplog.records]
    assert any(str(html_file) in message and "descripton" in message for message in warnings)
    assert any(
        str(html_file) in message
        and all(part in message for part in ("publisher", "logo", "urll"))
        for message in warnings
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("invalid_field", "invalid_value", "expected_title", "expected_description", "expected_dates"),
    [
        ("author", {"@type": "Organization", "name": 42}, "Article title", "Article description", True),
        ("publisher", {"logo": {"url": 42}}, "Article title", "Article description", True),
        ("name", 42, "Fallback title", "", False),
        ("dateModified", "not-a-date", "Fallback title", "", False),
    ],
    ids=["invalid-author", "invalid-logo", "invalid-title", "invalid-date"],
)
async def test_json_ld_invalid_fields_preserve_or_fallback_frontmatter(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    invalid_field: str,
    invalid_value: object,
    expected_title: str,
    expected_description: str,
    expected_dates: bool,
) -> None:
    """Preserve core values for invalid nested data and retain core fallback."""
    payload = {
        "name": "Article title",
        "description": "Article description",
        "dateCreated": "2026-01-02",
        "dateModified": "2026-02-03",
        "datePublished": "2026-03-04",
        invalid_field: invalid_value,
    }
    html_file = tmp_path / "index.html"
    html_file.write_text(
        '<html><head><script type="application/ld+json">'
        f'{json.dumps(payload)}</script></head><body><h1>Article</h1></body></html>',
        encoding="utf-8",
    )

    with caplog.at_level("WARNING", logger="docbuild.tasks.build.llms.generator"):
        await process_single_html_file(
            html_file, tmp_path, tmp_path / "docs", "docs", "guides",
            "Fallback title", only_md=True,
        )

    assert any(
        str(html_file) in record.getMessage() and invalid_field in record.getMessage()
        for record in caplog.records
    )
    markdown = (tmp_path / "docs/guides/index.md").read_text(encoding="utf-8")
    frontmatter = yaml.safe_load(markdown.split("---")[1])
    assert frontmatter["title"] == expected_title
    assert frontmatter["description"] == expected_description
    dates = {key: value for key, value in frontmatter.items() if key.startswith("date")}
    assert dates == (
        {
            "dateCreated": "2026-01-02",
            "dateModified": "2026-02-03",
            "datePublished": "2026-03-04",
        }
        if expected_dates else {}
    )


def test_json_ld_reports_unknown_fields_with_invalid_values(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Report unknown properties even when other properties are invalid."""
    html_file = tmp_path / "article.html"
    payload = {
        "name": 42,
        "descripton": "Typo",
        "publisher": {"logo": {"url": 42, "urll": "Typo"}},
    }
    html = f'<script type="application/ld+json">{json.dumps(payload)}</script>'

    with caplog.at_level("WARNING", logger="docbuild.tasks.build.llms.generator"):
        assert extract_json_ld(html, html_file) is None

    assert "descripton" in caplog.text
    assert "publisher.logo.urll" in caplog.text


def test_json_ld_invalid_core_field_name_uses_fallback(tmp_path: Path) -> None:
    """Treat accepted Python field names like their JSON aliases."""
    payload = {"name": "Title", "date_modified": "invalid"}
    html = f'<script type="application/ld+json">{json.dumps(payload)}</script>'

    assert extract_json_ld(html, tmp_path / "article.html") is None


@pytest.mark.parametrize(
        "generator_meta",
        ["", '<meta name="generator" content="DAPS 4.0">'],
        ids=["without-generator", "with-generator"],
)
def test_clean_and_convert_daps_page_chrome(generator_meta: str) -> None:
        """Remove DAPS navigation chrome while preserving document content."""
        html = f"""<!DOCTYPE html>
        <html>
            <head>{generator_meta}<title>Introduction to Valkey</title></head>
            <body>
                <div class="bypass-block">
                    <a href="#_content">Jump to content</a>
                    <a href="#_bottom-pagination">Jump to page navigation</a>
                </div>
                <header id="_mainnav">
                    <img src="static/images/logo.svg" alt="Logo">
                </header>
                <div class="crumbs">
                    <a class="crumb" href="index.html">Introduction to Valkey</a>
                </div>
                <main id="_content">
                    <nav id="_side-toc-overall" class="side-toc">
                        <div class="side-title">Introduction to Valkey</div>
                    </nav>
                    <article class="documentation">
                        <h1>Introduction to Valkey</h1>
                        <p>Install and configure Valkey.</p>
                        <img src="images/valkey.png" alt="Valkey architecture">
                    </article>
                </main>
                <footer>Site footer</footer>
            </body>
        </html>"""

        assert isinstance(get_cleaner(JustHTML(html, sanitize=False)), DocBookHTMLCleaner)
        md = clean_and_convert(html)

        assert md.lstrip().startswith("# Introduction to Valkey")
        assert md.count("Introduction to Valkey") == 1
        assert "Install and configure Valkey." in md
        assert "![Valkey architecture](images/valkey.png)" in md
        assert "Jump to" not in md
        assert "static/images/logo.svg" not in md
        assert "Site footer" not in md


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
    assert md.lstrip().startswith("# Identifying Operating Systems")
    assert "<table" not in md
    assert "<img" not in md
    assert "| Attribute | Meaning | Value |" in md
    assert "| `NAME` | Full name of the distribution | SLES |" in md
    assert (
        "> [!NOTE]\n> **Different content for SUSE Linux 16.0 and SUSE Linux Micro 6.2**"
        in md
    )
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
    assert md.lstrip().startswith("# 8 Boot parameters")
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
    assert "> [!WARNING]\n> After you set the Rancher Server URL" in md
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
    assert "> [!CAUTION]\n> Plain text content" in md
    assert "> [!IMPORTANT]\n> Important text" in md
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
