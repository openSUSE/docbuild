"""Build readable, semantic XPath expressions for XML nodes.

The helper in this module prefers stable attribute-based predicates like
``@id`` and ``@lang`` where possible and falls back to positional predicates
for ambiguous siblings.
"""

from lxml import etree


def xpath_literal(value: str) -> str:
    """Return ``value`` as a safely escaped XPath string literal.

    :param value: Arbitrary text value that will be embedded in an XPath predicate.
    :returns: A valid XPath literal expression.
    """
    if "'" not in value:
        return f"'{value}'"
    if '"' not in value:
        return f'"{value}"'

    parts = value.split("'")
    quoted_parts = ", \"'\", ".join(f"'{part}'" for part in parts)
    return f"concat({quoted_parts})"


def position_among_same_tag_siblings(node: etree._Element) -> int:
    """Return the 1-based position among same-tag siblings.

    :param node: Node whose sibling position should be computed.
    :returns: Position among siblings with the same element name.
    """
    parent = node.getparent()
    if parent is None:
        return 1

    node_name = etree.QName(node).localname
    same_tag_siblings = [
        child
        for child in parent
        if isinstance(child.tag, str) and etree.QName(child).localname == node_name
    ]
    return same_tag_siblings.index(node) + 1


def is_unique_among_same_tag_siblings(node: etree._Element, attr: str, value: str) -> bool:
    """Return whether ``attr=value`` uniquely identifies ``node`` among siblings.

    :param node: Node to validate.
    :param attr: Attribute name to test.
    :param value: Attribute value to test.
    :returns: ``True`` if no sibling with same tag shares ``attr=value``.
    """
    parent = node.getparent()
    if parent is None:
        return True

    node_name = etree.QName(node).localname
    matches = 0
    for sibling in parent:
        if not isinstance(sibling.tag, str):
            continue
        if etree.QName(sibling).localname != node_name:
            continue
        if sibling.get(attr) == value:
            matches += 1
            if matches > 1:
                return False
    return matches == 1


def preferred_predicate_attributes(node_name: str) -> tuple[str, ...]:
    """Return preferred attribute keys for semantic predicates.

    :param node_name: XML element local name.
    :returns: Ordered attribute names to try for predicate generation.
    """
    preferred_keys: dict[str, tuple[str, ...]] = {
        "portal": ("id",),
        "product": ("id",),
        "docset": ("id",),
        "locale": ("lang",),
        "deliverable": ("id",),
        "category": ("lang",),
        "language": ("id", "linkend"),
        "item": ("id",),
        "desc": ("lang",),
        "dc": ("file",),
    }
    fallback = ("id", "lang", "name", "key")
    return preferred_keys.get(node_name, fallback)


def semantic_xpath(node: etree._Element) -> str:
    """Build a readable absolute XPath for ``node``.

    The function prefers stable attribute predicates where possible and falls
    back to positional predicates when attributes are missing or ambiguous.

    :param node: Target XML element.
    :returns: Absolute XPath expression for the provided node.
    """
    parts: list[str] = []
    current: etree._Element | None = node

    while current is not None:
        node_name = etree.QName(current).localname

        if current.getparent() is None:
            parts.append(node_name)
            current = current.getparent()
            continue

        predicate: str | None = None

        for attr in preferred_predicate_attributes(node_name):
            value = current.get(attr)
            if value and is_unique_among_same_tag_siblings(current, attr, value):
                predicate = f"@{attr}={xpath_literal(value)}"
                break

        if predicate is None:
            predicate = str(position_among_same_tag_siblings(current))

        parts.append(f"{node_name}[{predicate}]")
        current = current.getparent()

    parts.reverse()
    return "/" + "/".join(parts)
