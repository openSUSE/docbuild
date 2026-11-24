"""DOM manipulation utilities for LLM Markdown conversion."""

import re

from justhtml.dom import Element, Node, NodeType, Text

GFM_ADMONITION_TYPES = {"note", "tip", "important", "warning", "caution"}


def get_attrs(node: NodeType) -> dict[str, str]:
    """Extract attributes from a DOM node as a string dictionary."""
    if not isinstance(node, Node) or node.attrs is None:
        return {}
    return {key: value or "" for key, value in node.attrs.items()}


def get_classes(node: NodeType) -> list[str]:
    """Return the list of CSS classes on a DOM node."""
    return get_attrs(node).get("class", "").split()


def is_empty_removable(node: NodeType) -> bool:
    """Check if an anchor or list item is empty and should be removed."""
    if not isinstance(node, Node) or node.name.lower() not in {"a", "li"}:
        return False
    if node.to_text(strip=True):
        return False
    return not (node.query("img") or node.query("table"))


def unwrap_li_paragraphs(node: Node) -> None:
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
        c in {"paragraph", "para"} for c in get_classes(first)
    ):
        first.name = "span"
        for sub in getattr(first, "children", None) or []:
            if str(getattr(sub, "name", "")).lower() == "p":
                sub.name = "span"
                break
    elif first_tag == "p":
        first.name = "span"


def resolve_admonition_type(node: Node, fallback: str = "note") -> str:
    """Return the uppercase GitHub alert type for an admonition node."""
    for cls in get_classes(node):
        if cls.lower() in GFM_ADMONITION_TYPES:
            return cls.upper()
    return fallback.upper() if fallback.lower() in GFM_ADMONITION_TYPES else "NOTE"


def convert_antora_admonition(node: Node) -> None:
    """Convert Antora table-based admonition blocks into GitHub alert blockquotes."""
    content_td = node.query_one("td.content")
    if content_td is None:
        return

    fallback = "note"
    icon_el = node.query_one("td.icon i")
    title_el = node.query_one("td.icon .title")
    if icon_el and get_attrs(icon_el).get("title"):
        fallback = get_attrs(icon_el)["title"].strip()
    elif title_el and title_el.to_text(strip=True):
        fallback = title_el.to_text(strip=True)

    alert_type = resolve_admonition_type(node, fallback=fallback)

    node.name = "blockquote"
    marker = Element("p", {}, "html")
    marker.append_child(Text(f"[!{alert_type}]"))

    node.children = [marker, *(content_td.children or [])]
    for child in node.children:
        child.parent = node


def convert_docbook_admonition(node: Node) -> None:
    """Convert DocBook admonition divs into GitHub alert blockquotes."""
    alert_type = resolve_admonition_type(node)
    node.name = "blockquote"

    new_children: list[NodeType] = []
    marker = Element("p", {}, "html")
    marker.append_child(Text(f"[!{alert_type}]"))
    new_children.append(marker)

    prefix_pattern = re.compile(rf"^{alert_type}\s*:?\s*", re.IGNORECASE)

    for child in list(node.children or []):
        if "admon-title" in get_classes(child):
            title_text = prefix_pattern.sub("", child.to_text(strip=True)).strip()
            if title_text:
                p_title = Element("p", {}, "html")
                strong = Element("strong", {}, "html")
                strong.append_child(Text(title_text))
                p_title.append_child(strong)
                new_children.append(p_title)
        else:
            new_children.append(child)

    node.children = new_children
    for child in node.children:
        child.parent = node


def normalize_node(node: NodeType) -> None:
    """Normalize text spacing, headings, list items, and admonitions."""
    if isinstance(node, Text):
        if isinstance(node.data, str) and "\xa0" in node.data:
            node.data = node.data.replace("\xa0", " ")
        return

    tag = node.name.lower()
    classes = get_classes(node)

    if tag == "span" and any(c in {"title-number", "number"} for c in classes):
        text = node.to_text(strip=False)
        if text and not text[-1].isspace():
            node.append_child(Text(" "))
    elif tag == "li":
        unwrap_li_paragraphs(node)
    elif tag == "div":
        if "admonitionblock" in classes:
            convert_antora_admonition(node)
        elif "admonition" in classes:
            convert_docbook_admonition(node)


def replace_node(target: NodeType, replacement: NodeType | None) -> None:
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

    target.parent = None
