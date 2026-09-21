"""Utilities for generating Markdown and llms.txt files from HTML."""

from html.parser import HTMLParser
from io import StringIO

from justhtml import JustHTML

# Standard HTML5 void elements that cannot contain children or have closing tags
VOID_ELEMENTS: set[str] = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr"
}


class HTMLStripper(HTMLParser):
    """A robust HTML parser that strips out specific tags, IDs, and classes.

    It works recursively, preserving character entities and valid HTML syntax.
    """

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

        # Reconstruct standard start tag
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


def clean_and_convert(html_content: str) -> str:
    """Parse HTML, remove unwanted layout blocks, and convert to Markdown."""
    tags_to_strip = ["nav", "header", "footer", "aside"]
    ids_to_strip = [
        "_side-toc-overall",
        "_side-toc-page",
        "navbar",
        "toc",
        "_mainnav",
        "_unfold-side-toc-page"
    ]
    classes_to_strip = [
        "navbar", "toc", "table-of-contents", "bypass-block",
        "crumbs", "bottom-pagination", "side-toc",
        "permalink",          # Strip out permalinks
        "icon-editsource",    # Strip out the edit source button
        "icon-reportbug"      # Strip out the bug report button
    ]

    stripper = HTMLStripper(tags_to_strip, ids_to_strip, classes_to_strip)
    stripper.feed(html_content)
    clean_html = stripper.get_clean_html()

    doc = JustHTML(clean_html)
    return doc.to_markdown()


def inject_llms_links(html_content: str, md_rel_path: str, llmstxt_rel_path: str) -> str:
    """Safely inject alternate link tags into the <head> of the HTML."""
    md_link = f'<link rel="alternate" type="text/markdown" href="{md_rel_path}">'
    llms_link = f'<link rel="alternate" type="text/markdown" href="{llmstxt_rel_path}">'

    # Safe injection right before the closing head tag
    head_close = "</head>"
    if head_close in html_content:
        injection = f"    {md_link}\n    {llms_link}\n</head>"
        return html_content.replace(head_close, injection, 1)

    # Fallback if no </head> exists (rare, but safe)
    return html_content
