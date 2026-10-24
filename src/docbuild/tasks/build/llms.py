"""Utilities for generating Markdown and llms.txt files from HTML."""

from html import escape
from typing import Final

from justhtml import JustHTML


class HTMLCleaner:
    """Base class to strip specific tags, IDs, and classes using DOM traversal."""

    VOID_ELEMENTS: Final[frozenset[str]] = frozenset({
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr"
    })

    def __init__(self, tags_to_strip: list[str] | None, ids_to_strip: list[str] | None, classes_to_strip: list[str] | None) -> None:
        """Initialize the HTML stripper with target elements to remove."""
        self.tags_to_strip = frozenset(tags_to_strip or [])
        self.ids_to_strip = frozenset(ids_to_strip or [])
        self.classes_to_strip = frozenset(classes_to_strip or [])

    def should_strip(self, node: object) -> bool:
        """Determine if a DOM node should be stripped."""
        # JustHTML stores the tag name in the .name attribute
        node_name = getattr(node, "name", None)
        if not node_name:
            return False

        tag = str(node_name).lower()

        # Safely extract attributes (handling None, dicts, and lists of tuples)
        raw_attrs = getattr(node, "attrs", None)
        if raw_attrs is None:
            attrs = {}
        elif isinstance(raw_attrs, list):
            attrs = {k: v or "" for k, v in raw_attrs}
        else:
            attrs = dict(raw_attrs)

        node_id = attrs.get("id", "")
        node_classes = attrs.get("class", "").split()

        return (
            tag in self.tags_to_strip or
            node_id in self.ids_to_strip or
            any(cls in self.classes_to_strip for cls in node_classes)
        )

    def clean(self, node: object) -> None:
        """Recursively clean the DOM tree in place."""
        children = getattr(node, "children", None)
        if not children:
            return

        # Iterate backwards to safely pop items from the list without skipping indexes
        for i in range(len(children) - 1, -1, -1):
            child = children[i]
            if self.should_strip(child):
                children.pop(i)
            else:
                self.clean(child)


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


def detect_generator(doc: JustHTML) -> str | None:
    """Detect the HTML type from the <meta name="generator"> tag."""
    target_generators: Final[tuple[str, ...]] = ("daps", "docbook", "antora")

    for meta in doc.query("meta"):
        attrs = getattr(meta, "attrs", {})
        name = attrs.get("name", "").lower()

        if name == "generator":
            content = attrs.get("content", "").lower()
            for gen in target_generators:
                if gen in content:
                    return gen
    return None


def get_cleaner(doc: JustHTML) -> HTMLCleaner:
    """Return the appropriate HTMLCleaner instance based on the document type."""
    generator = detect_generator(doc)

    match generator:
        case "antora":
            return AntoraHTMLCleaner()
        case "daps" | "docbook":
            return DocBookHTMLCleaner()
        case _:
            return HTMLCleaner(None, None, None)


def clean_and_convert(html_content: str) -> str:
    """Parse HTML into a DOM tree, clean it, and convert to Markdown."""
    doc = JustHTML(html_content, sanitize=False)
    cleaner = get_cleaner(doc)

    # Mutate the DOM tree in place
    cleaner.clean(doc.root)

    return doc.to_markdown()


def inject_llms_links(html_content: str, md_rel_path: str, llmstxt_rel_path: str) -> str:
    """Inject alternate markdown link tags into the <head> of an HTML document."""
    doc = JustHTML(html_content, sanitize=False)
    head = doc.query_one("head")

    if head is None:
        target_parent = doc.query_one("html") or doc.root
        parsed_head = JustHTML("<head></head>", fragment=True, sanitize=False).root

        # Safely extract the created <head> node
        if not parsed_head.children:
            return doc.to_html()

        head = parsed_head.children[0]
        head.parent = target_parent

        # Ensure children list exists before inserting
        if target_parent.children is None:
            target_parent.children = []
        target_parent.children.insert(0, head)

    safe_md_path = escape(md_rel_path, quote=True)
    safe_llms_path = escape(llmstxt_rel_path, quote=True)

    md_markup = f'<link rel="alternate" type="text/markdown" href="{safe_md_path}">'
    llms_markup = f'<link rel="alternate" type="text/markdown" href="{safe_llms_path}">'

    parsed_md = JustHTML(md_markup, fragment=True, sanitize=False).root
    parsed_llms = JustHTML(llms_markup, fragment=True, sanitize=False).root

    # Safely extract the link nodes and append them
    if parsed_md.children and parsed_llms.children:
        md_node = parsed_md.children[0]
        llms_node = parsed_llms.children[0]

        md_node.parent = head
        llms_node.parent = head

        if head.children is None:
            head.children = []
        head.children.extend([md_node, llms_node])

    return doc.to_html()
