"""Markdown conversion utilities for tables and images."""

import re
from urllib.parse import quote

from justhtml.dom import Element, Node, Text

from docbuild.tasks.build.llms.dom import get_attrs, replace_node


def format_table_cell(cell: Node, placeholders: dict[str, str]) -> str:
    """Convert a table cell DOM node into a single-line Markdown string."""
    text: str = cell.to_markdown()
    for key, val in placeholders.items():
        text = text.replace(key, val)
    collapsed = " ".join(text.split())
    return re.sub(r"(?<!\\)\|", r"\|", collapsed)


def table_to_markdown(table: Node, placeholders: dict[str, str]) -> str:
    """Convert an HTML table DOM node into a GFM pipe table."""
    rows: list[list[str]] = []
    has_header = bool(table.query("thead"))

    for tr in table.query("tr"):
        cells = [
            format_table_cell(cell, placeholders)
            for cell in (tr.children or [])
            if isinstance(cell, Node) and cell.name.lower() in {"th", "td"}
        ]
        if cells:
            if not rows:
                has_header = has_header or any(
                    isinstance(cell, Node) and cell.name.lower() == "th"
                    for cell in (tr.children or [])
                )
            rows.append(cells)

    if not rows:
        return ""

    num_cols = max(len(row) for row in rows)
    padded = [row + [""] * (num_cols - len(row)) for row in rows]

    if has_header:
        header = padded[0]
        body = padded[1:]
    else:
        header = [""] * num_cols
        body = padded

    header_line = "| " + " | ".join(header) + " |"
    separator = "| " + " | ".join(["---"] * num_cols) + " |"
    body_lines = ["| " + " | ".join(row) + " |" for row in body]
    return "\n".join([header_line, separator, *body_lines])


def img_to_markdown(img: Node) -> str:
    """Convert an HTML img DOM node into a Markdown image string."""
    attrs = get_attrs(img)
    src = attrs.get("src", "").strip()
    if not src:
        return ""

    src = quote(src, safe="/:?&=#%")
    alt = " ".join(attrs.get("alt", "").split())
    return f"![{alt}]({src})"


def replace_tables_and_images(root: Node) -> dict[str, str]:
    """Replace img and table DOM nodes with Markdown placeholder tokens."""
    placeholders: dict[str, str] = {}
    counter = 0

    for img in list(root.query("img")):
        md_img = img_to_markdown(img)
        if md_img:
            key = f"DOCBUILDMDIMG{counter}END"
            counter += 1
            placeholders[key] = md_img
            replace_node(img, Text(key))
        else:
            replace_node(img, None)

    for table in reversed(list(root.query("table"))):
        md_table = table_to_markdown(table, placeholders)
        if md_table:
            key = f"DOCBUILDMDTBL{counter}END"
            counter += 1
            placeholders[key] = md_table
            p_node = Element("p", {}, "html")
            p_node.append_child(Text(key))
            replace_node(table, p_node)
        else:
            replace_node(table, None)

    return placeholders
