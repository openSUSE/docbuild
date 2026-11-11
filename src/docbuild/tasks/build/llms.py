"""Utilities for generating Markdown and llms.txt files from HTML."""

from html import escape
import re
from typing import Final

from justhtml import JustHTML
from justhtml.dom import Element, Node, NodeType, Text


def _get_attrs(node: object) -> dict[str, str]:
    """Extract attributes from a DOM node as a string dictionary."""
    raw_attrs = getattr(node, "attrs", None)
    if raw_attrs is None:
        return {}
    if isinstance(raw_attrs, list):
        return {str(k): str(v or "") for k, v in raw_attrs}
    return {str(k): str(v or "") for k, v in dict(raw_attrs).items()}


def _get_classes(node: object) -> list[str]:
    """Return the list of CSS classes on a DOM node."""
    return _get_attrs(node).get("class", "").split()


def _is_empty_removable(node: NodeType) -> bool:
    """Check if an anchor or list item is empty and should be removed."""
    if not isinstance(node, Node) or node.name.lower() not in {"a", "li"}:
        return False
    if node.to_text(strip=True):
        return False
    return not (node.query("img") or node.query("table"))


def _unwrap_li_paragraphs(node: Node) -> None:
    """Convert leading paragraph wrappers in list items to inline spans."""
    children = node.children
    if not children:
        return

    while children and getattr(children[0], "name", "") == "#text":
        if not str(getattr(children[0], "data", "")).strip():
            children.pop(0)
        else:
            break

    if not children:
        return

    first = children[0]
    first_tag = str(getattr(first, "name", "")).lower()
    if first_tag == "div" and any(
        c in {"paragraph", "para"} for c in _get_classes(first)
    ):
        first.name = "span"
        for sub in getattr(first, "children", None) or []:
            if str(getattr(sub, "name", "")).lower() == "p":
                sub.name = "span"
                break
    elif first_tag == "p":
        first.name = "span"


def _convert_antora_admonition(node: Node) -> None:
    """Convert Antora table-based admonition blocks into blockquotes."""
    content_td = node.query_one("td.content")
    if content_td is None:
        return

    label = "Note"
    icon_el = node.query_one("td.icon i")
    title_el = node.query_one("td.icon .title")
    if icon_el and _get_attrs(icon_el).get("title"):
        label = _get_attrs(icon_el)["title"].strip()
    elif title_el and title_el.to_text(strip=True):
        label = title_el.to_text(strip=True)
    else:
        for cls in _get_classes(node):
            if cls in {"note", "tip", "warning", "important", "caution"}:
                label = cls.capitalize()
                break

    node.name = "blockquote"
    strong = Element("strong", {}, "html")
    strong.append_child(Text(f"{label}: "))

    first_p = content_td.query_one("p")
    if first_p is not None and first_p.children is not None:
        first_p.children.insert(0, strong)
        strong.parent = first_p
        node.children = list(content_td.children or [])
    else:
        p_node = Element("p", {}, "html")
        p_node.append_child(strong)
        node.children = [p_node, *(content_td.children or [])]

    for child in node.children:
        child.parent = node


def _convert_docbook_admonition(node: Node) -> None:
    """Convert DocBook admonition divs into blockquotes with bold titles."""
    node.name = "blockquote"
    for child in node.children or []:
        if "admon-title" in _get_classes(child):
            child.name = "p"
            strong = Element("strong", {}, "html")
            for sub in list(child.children or []):
                strong.append_child(sub)
            child.children = [strong]
            strong.parent = child


def _normalize_node(node: NodeType) -> None:
    """Normalize text spacing, headings, list items, and admonitions."""
    if isinstance(node, Text):
        if isinstance(node.data, str) and "\xa0" in node.data:
            node.data = node.data.replace("\xa0", " ")
        return

    tag = node.name.lower()
    classes = _get_classes(node)

    if tag == "span" and any(c in {"title-number", "number"} for c in classes):
        text = node.to_text(strip=False)
        if text and not text[-1].isspace():
            node.append_child(Text(" "))
    elif tag == "li":
        _unwrap_li_paragraphs(node)
    elif tag == "div":
        if "admonitionblock" in classes:
            _convert_antora_admonition(node)
        elif "admonition" in classes:
            _convert_docbook_admonition(node)


def _format_table_cell(cell: Node, placeholders: dict[str, str]) -> str:
    """Convert a table cell DOM node into a single-line Markdown string."""
    text: str = cell.to_markdown()
    for key, val in placeholders.items():
        text = text.replace(key, val)
    collapsed = " ".join(text.split())
    return re.sub(r"(?<!\\)\|", r"\|", collapsed)


def _table_to_markdown(table: Node, placeholders: dict[str, str]) -> str:
    """Convert an HTML table DOM node into a GFM pipe table."""
    rows: list[list[str]] = []
    for tr in table.query("tr"):
        cells = [
            _format_table_cell(c, placeholders)
            for c in (tr.children or [])
            if isinstance(c, Node) and c.name.lower() in {"th", "td"}
        ]
        if cells:
            rows.append(cells)

    if not rows:
        return ""

    num_cols = max(len(r) for r in rows)
    padded = [r + [""] * (num_cols - len(r)) for r in rows]

    header = "| " + " | ".join(padded[0]) + " |"
    sep = "| " + " | ".join(["---"] * num_cols) + " |"
    body = ["| " + " | ".join(r) + " |" for r in padded[1:]]
    return "\n".join([header, sep, *body])


def _img_to_markdown(img: Node) -> str:
    """Convert an HTML img DOM node into a Markdown image string."""
    attrs = _get_attrs(img)
    src = attrs.get("src", "").strip()
    if not src:
        return ""
    alt = " ".join(attrs.get("alt", "").split())
    return f"![{alt}]({src})"


def _replace_node(target: NodeType, replacement: NodeType | None) -> None:
    """Replace or remove a DOM node in its parent's children list."""
    parent = target.parent
    children = getattr(parent, "children", None)
    if not children or target not in children:
        return
    idx = children.index(target)
    if replacement is None:
        children.pop(idx)
    else:
        replacement.parent = parent
        children[idx] = replacement


def _replace_tables_and_images(root: Node) -> dict[str, str]:
    """Replace img and table DOM nodes with Markdown placeholder tokens."""
    placeholders: dict[str, str] = {}
    counter = 0

    for img in list(root.query("img")):
        md_img = _img_to_markdown(img)
        if md_img:
            key = f"DOCBUILDMDIMG{counter}END"
            counter += 1
            placeholders[key] = md_img
            _replace_node(img, Text(key))
        else:
            _replace_node(img, None)

    for table in reversed(list(root.query("table"))):
        md_table = _table_to_markdown(table, placeholders)
        if md_table:
            key = f"DOCBUILDMDTBL{counter}END"
            counter += 1
            placeholders[key] = md_table
            p_node = Element("p", {}, "html")
            p_node.append_child(Text(key))
            _replace_node(table, p_node)
        else:
            _replace_node(table, None)

    return placeholders


class HTMLCleaner:
    """Base class to strip specific tags, IDs, and classes using DOM traversal."""

    VOID_ELEMENTS: Final[frozenset[str]] = frozenset(
        {
            "area",
            "base",
            "br",
            "col",
            "embed",
            "hr",
            "img",
            "input",
            "link",
            "meta",
            "param",
            "source",
            "track",
            "wbr",
        }
    )

    def __init__(
        self,
        tags_to_strip: list[str] | None,
        ids_to_strip: list[str] | None,
        classes_to_strip: list[str] | None,
    ) -> None:
        """Initialize the HTML stripper with target elements to remove."""
        base_tags = {"script", "style", "noscript", "button", "svg", "shared-header"}
        self.tags_to_strip = frozenset(base_tags | set(tags_to_strip or []))
        self.ids_to_strip = frozenset(ids_to_strip or [])
        self.classes_to_strip = frozenset(classes_to_strip or [])

    def should_strip(self, node: object) -> bool:
        """Determine if a DOM node should be stripped."""
        node_name = getattr(node, "name", None)
        if not node_name:
            return False

        tag = str(node_name).lower()
        attrs = _get_attrs(node)
        node_id = attrs.get("id", "")
        node_classes = attrs.get("class", "").split()

        return (
            tag in self.tags_to_strip
            or node_id in self.ids_to_strip
            or any(cls in self.classes_to_strip for cls in node_classes)
        )

    def clean(self, node: NodeType) -> None:
        """Recursively clean and normalize the DOM tree in place."""
        children = getattr(node, "children", None)
        if children:
            for i in range(len(children) - 1, -1, -1):
                child = children[i]
                if self.should_strip(child):
                    children.pop(i)
                else:
                    self.clean(child)
                    if _is_empty_removable(child):
                        children.pop(i)

        _normalize_node(node)


class DocBookHTMLCleaner(HTMLCleaner):
    """HTML Cleaner tailored for DAPS/DocBook output."""

    def __init__(self) -> None:
        """Initialize cleaner with DAPS/DocBook specific rules."""
        super().__init__(
            tags_to_strip=["nav", "header", "footer", "aside"],
            ids_to_strip=[
                "_side-toc-overall",
                "_side-toc-page",
                "navbar",
                "toc",
                "_mainnav",
                "_unfold-side-toc-page",
                "_open-side-toc-overall",
                "searchUnifyChatbot",
                "qualtrics_container",
            ],
            classes_to_strip=[
                "navbar",
                "toc",
                "table-of-contents",
                "bypass-block",
                "crumbs",
                "bottom-pagination",
                "side-toc",
                "permalink",
                "icon-editsource",
                "icon-reportbug",
                "icons",
                "symbol",
                "date",
                "titlepage-revhistory",
            ],
        )


class AntoraHTMLCleaner(HTMLCleaner):
    """HTML Cleaner tailored for Antora output."""

    def __init__(self) -> None:
        """Initialize cleaner with Antora specific rules."""
        super().__init__(
            tags_to_strip=["nav", "header", "footer", "aside"],
            ids_to_strip=["topbar-nav"],
            classes_to_strip=[
                "nav-panel-menu",
                "nav-panel-explore",
                "toc",
                "nav-container",
                "footer",
                "toolbar",
                "nav-wrapper",
                "breadcrumbs",
                "anchor",
            ],
        )


def detect_generator(doc: JustHTML) -> str | None:
    """Detect the HTML type from the <meta name="generator"> tag."""
    target_generators: Final[tuple[str, ...]] = ("daps", "docbook", "antora")

    for meta in doc.query("meta"):
        attrs = _get_attrs(meta)
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
    placeholders = _replace_tables_and_images(doc.root)

    md: str = doc.to_markdown()
    for key, val in placeholders.items():
        md = md.replace(key, val)
    return md


def inject_llms_links(
    html_content: str, md_rel_path: str, llmstxt_rel_path: str
) -> str:
    """Inject alternate markdown link tags into the <head> of an HTML document."""
    doc = JustHTML(html_content, sanitize=False)
    head = doc.query_one("head")

    if head is None:
        target_parent = doc.query_one("html") or doc.root
        head = Element("head", {}, "html")
        head.parent = target_parent
        if target_parent.children is None:
            target_parent.children = []
        target_parent.children.insert(0, head)

    safe_md_path = escape(md_rel_path, quote=True)
    safe_llms_path = escape(llmstxt_rel_path, quote=True)

    md_markup = f'<link rel="alternate" type="text/markdown" href="{safe_md_path}">'
    llms_markup = f'<link rel="alternate" type="text/markdown" href="{safe_llms_path}">'

    parsed_md = JustHTML(md_markup, fragment=True, sanitize=False).root
    parsed_llms = JustHTML(llms_markup, fragment=True, sanitize=False).root

    if parsed_md.children and parsed_llms.children:
        head.append_child(parsed_md.children[0])
        head.append_child(parsed_llms.children[0])

    return doc.to_html()
