"""Utilities for generating Markdown and llms.txt files from HTML."""

from html import escape
from html.parser import HTMLParser
from io import StringIO
import re

from justhtml import JustHTML

# Standard HTML5 void elements that cannot contain children or have closing tags
VOID_ELEMENTS: set[str] = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr"
}


class HTMLCleaner(HTMLParser):
    """Base class to strip specific tags, IDs, and classes."""

    def __init__(self, tags_to_strip: list[str], ids_to_strip: list[str], classes_to_strip: list[str]) -> None:
        """Initialize the HTML stripper with target elements to remove."""
        super().__init__(convert_charrefs=False)
        self.tags_to_strip = set(tags_to_strip)
        self.ids_to_strip = set(ids_to_strip)
        self.classes_to_strip = set(classes_to_strip)
        self.result = StringIO()
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Process an opening HTML tag and drop it if it matches strip criteria."""
        attrs_dict = {k: v or "" for k, v in attrs}
        tag_id = attrs_dict.get("id", "")
        tag_classes = attrs_dict.get("class", "").split()

        should_strip = (
            tag in self.tags_to_strip or
            tag_id in self.ids_to_strip or
            any(cls in self.classes_to_strip for cls in tag_classes)
        )

        if should_strip:
            if tag not in VOID_ELEMENTS:
                self.skip_depth += 1
            return

        if self.skip_depth > 0:
            if tag not in VOID_ELEMENTS:
                self.skip_depth += 1
            return

        attr_str = "".join(f' {k}="{v}"' if v is not None else f' {k}' for k, v in attrs)
        self.result.write(f"<{tag}{attr_str}>")

    def handle_endtag(self, tag: str) -> None:
        """Process a closing HTML tag."""
        if self.skip_depth > 0:
            if tag not in VOID_ELEMENTS:
                self.skip_depth -= 1
            return
        self.result.write(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        """Process text data between tags."""
        if self.skip_depth == 0:
            self.result.write(data)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Process an empty HTML tag (like <br/> or <img/>)."""
        attrs_dict = {k: v or "" for k, v in attrs}
        tag_id = attrs_dict.get("id", "")
        tag_classes = attrs_dict.get("class", "").split()

        should_strip = (
            tag in self.tags_to_strip or
            tag_id in self.ids_to_strip or
            any(cls in self.classes_to_strip for cls in tag_classes)
        )

        if should_strip or self.skip_depth > 0:
            return

        attr_str = "".join(f' {k}="{v}"' if v is not None else f' {k}' for k, v in attrs)
        self.result.write(f"<{tag}{attr_str} />")

    def handle_entityref(self, name: str) -> None:
        """Process a general entity reference."""
        if self.skip_depth == 0:
            self.result.write(f"&{name};")

    def handle_charref(self, name: str) -> None:
        """Process a numeric character reference."""
        if self.skip_depth == 0:
            self.result.write(f"&#{name};")

    def handle_comment(self, data: str) -> None:
        """Process an HTML comment."""
        if self.skip_depth == 0:
            self.result.write(f"<!--{data}-->")

    def handle_decl(self, decl: str) -> None:
        """Process an HTML declaration."""
        if self.skip_depth == 0:
            self.result.write(f"<!{decl}>")

    def get_clean_html(self) -> str:
        """Return the fully cleaned HTML string."""
        return self.result.getvalue()


class DocBookHTMLCleaner(HTMLCleaner):
    """HTML Cleaner tailored for DAPS/DocBook output."""

    def __init__(self) -> None:
        super().__init__(
            tags_to_strip=["nav", "header", "footer", "aside"],
            ids_to_strip=[
                "_side-toc-overall", "_side-toc-page", "navbar", "toc",
                "_mainnav", "_unfold-side-toc-page"
            ],
            classes_to_strip=[
                "navbar", "toc", "table-of-contents", "bypass-block",
                "crumbs", "bottom-pagination", "side-toc", "permalink",
                "icon-editsource", "icon-reportbug"
            ]
        )


class AntoraHTMLCleaner(HTMLCleaner):
    """HTML Cleaner tailored for Antora output."""

    def __init__(self) -> None:
        super().__init__(
            tags_to_strip=["nav", "header", "footer", "aside"],
            ids_to_strip=["topbar-nav"],
            classes_to_strip=[
                "nav-panel-menu", "nav-panel-explore", "toc",
                "nav-container", "footer", "toolbar", "nav-wrapper", "breadcrumbs"
            ]
        )


def clean_and_convert(html_content: str) -> str:
    """Detect HTML type, clean it, and convert to Markdown."""
    generator_match = re.search(r'<meta\s+name=["\']generator["\']\s+content=["\']([^"\']+)["\']', html_content, re.IGNORECASE)
    generator = generator_match.group(1).lower() if generator_match else ""

    if "antora" in generator:
        cleaner = AntoraHTMLCleaner()
    else:
        cleaner = DocBookHTMLCleaner()

    cleaner.feed(html_content)
    clean_html = cleaner.get_clean_html()

    doc = JustHTML(clean_html)
    return doc.to_markdown()


def inject_llms_links(html_content: str, md_rel_path: str, llmstxt_rel_path: str) -> str:
    """Inject alternate markdown link tags into the <head> of an HTML document."""
    # Parse HTML without sanitization to preserve document head structure
    doc = JustHTML(html_content, sanitize=False)
    head = doc.query_one("head")

    # If <head> does not exist, create and prepend it to <html> or root
    if head is None:
        target_parent = doc.query_one("html") or doc.root
        head = JustHTML("<head></head>", fragment=True, sanitize=False).root.children[0]
        head.parent = target_parent
        target_parent.children.insert(0, head)

    # Sanitize attribute values against HTML injection
    safe_md_path = escape(md_rel_path, quote=True)
    safe_llms_path = escape(llmstxt_rel_path, quote=True)

    # Construct link fragments using JustHTML parser
    md_markup = f'<link rel="alternate" type="text/markdown" href="{safe_md_path}">'
    llms_markup = f'<link rel="alternate" type="text/markdown" href="{safe_llms_path}">'

    md_node = JustHTML(md_markup, fragment=True, sanitize=False).root.children[0]
    llms_node = JustHTML(llms_markup, fragment=True, sanitize=False).root.children[0]

    # Attach nodes to head element
    md_node.parent = head
    llms_node.parent = head
    head.children.extend([md_node, llms_node])

    return doc.to_html()
