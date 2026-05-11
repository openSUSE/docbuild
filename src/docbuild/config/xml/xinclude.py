"""Resolve XInclude and preserve source file metadata on inserted nodes.

Any XInclude element is replaced with the content of the included file,
and the included nodes are tagged with an ``xml:base`` attribute containing
the path to the included file relative to the root config file.

This allows to identify the source file for any node in the final merged XML tree, which is essential for validation.

Use :func:`~docbuild.config.xml.xinclude.parse_xml_with_xinclude_base` to
parse XML files with XInclude support:

.. code:: python

    tree = await await asyncio.to_thread(parse_xml_with_xinclude_base,
                                         "path/to/portal.xml")
    # Nodes from included files are tagged with xml:base
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from lxml import etree

from ...constants import XINCLUDE_NS, XML_NS

XML_BASE_ATTR = f"{{{XML_NS}}}base"
"""The fully qualified name of the ``xml:base`` attribute in Clark notation."""

XINCLUDE_TAG = f"{{{XINCLUDE_NS}}}include"
"""The fully qualified name of the ``xi:include`` element in Clark notation."""


def as_relative_posix(path: Path, root_dir: Path) -> str:
    """Return ``path`` relative to ``root_dir`` when possible."""
    resolved_path = path.resolve()
    resolved_root = root_dir.resolve()
    try:
        return resolved_path.relative_to(resolved_root).as_posix()
    except ValueError:
        return resolved_path.as_posix()


def xpointer_to_xpath(xpointer: str) -> str | None:
    """Extract XPath from ``xpointer(...)`` expressions."""
    text = xpointer.strip()
    prefix = "xpointer("
    if not text.startswith(prefix) or not text.endswith(")"):
        return None
    return text[len(prefix) : -1].strip()


def mark_source(nodes: list[etree._Element], source: str) -> list[etree._Element]:
    """Copy selected nodes and set their ``xml:base`` attribute."""
    copied: list[etree._Element] = []
    for node in nodes:
        node_copy = deepcopy(node)
        node_copy.set(XML_BASE_ATTR, source)
        copied.append(node_copy)
    return copied


def replace_include_with_nodes(
    include: etree._Element,
    nodes: list[etree._Element],
) -> None:
    """Replace one ``xi:include`` element with one or more resolved nodes."""
    parent = include.getparent()
    if parent is None:
        if len(nodes) == 1:
            include.getroottree()._setroot(nodes[0])
            return
        raise ValueError("Root-level xi:include must resolve to exactly one element")

    insert_at = parent.index(include)
    tail = include.tail
    parent.remove(include)
    for offset, node in enumerate(nodes):
        parent.insert(insert_at + offset, node)

    if tail and nodes:
        nodes[-1].tail = (nodes[-1].tail or "") + tail


def resolve_includes(
    tree: etree._ElementTree,
    *,
    current_path: Path,
    root_dir: Path,
    active_stack: set[Path],
) -> None:
    """Resolve all ``xi:include`` elements in ``tree`` recursively."""
    xincludes = tree.getroot().xpath(".//xi:include", namespaces={"xi": XINCLUDE_NS})
    for include in xincludes:
        if not isinstance(include, etree._Element):
            continue

        href = include.get("href")
        if not href:
            raise ValueError("xi:include without href is not supported")

        parse_mode = include.get("parse", "xml")
        if parse_mode != "xml":
            raise ValueError(f"Unsupported xi:include parse mode: {parse_mode}")

        include_path = (current_path.parent / href).resolve()
        if include_path in active_stack:
            raise ValueError(f"Recursive xi:include detected: {include_path}")

        included_tree = etree.parse(str(include_path), parser=None)
        active_stack.add(include_path)
        resolve_includes(
            included_tree,
            current_path=include_path,
            root_dir=root_dir,
            active_stack=active_stack,
        )
        active_stack.remove(include_path)

        source = as_relative_posix(include_path, root_dir)
        xpointer = include.get("xpointer")
        if xpointer:
            xpath = xpointer_to_xpath(xpointer)
            if not xpath:
                raise ValueError(f"Unsupported xi:include xpointer: {xpointer}")
            selected = included_tree.xpath(xpath)
            selected_elements = [node for node in selected if isinstance(node, etree._Element)]
            if not selected_elements:
                raise ValueError(
                    f"xi:include xpointer selected no elements: {xpointer}"
                )
            replacement_nodes = mark_source(selected_elements, source)
        else:
            replacement_nodes = mark_source([included_tree.getroot()], source)

        replace_include_with_nodes(include, replacement_nodes)


def parse_xml_with_xinclude_base(filepath: Path | str) -> etree._ElementTree:
    """Parse XML and resolve XIncludes while preserving include source paths.

    Nodes inserted from included files are stamped with ``xml:base`` so callers
    can report the originating source file after include expansion.

    :param filepath: Path to the root XML file.
    :returns: Parsed and include-resolved XML tree.
    """
    root_path = Path(filepath).resolve()
    tree = etree.parse(str(root_path), parser=None)
    active_stack = {root_path}
    resolve_includes(
        tree,
        current_path=root_path,
        root_dir=root_path.parent,
        active_stack=active_stack,
    )
    return tree
