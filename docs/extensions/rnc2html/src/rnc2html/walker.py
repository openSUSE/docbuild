"""
Schema traversal and documentation extraction.
"""
from dataclasses import dataclass, field

from lxml import etree  # type: ignore[import-untyped]

DOCBOOK_NS = "http://docbook.org/ns/docbook"
RNG_NS = "http://relaxng.org/ns/structure/1.0"
A_NS = "http://relaxng.org/ns/compatibility/annotations/1.0"

NAMESPACES = {
    "rng": RNG_NS,
    "db": DOCBOOK_NS,
    "a": A_NS,
}


@dataclass
class RncAttribute:
    name: str
    required: bool = False
    description: str | None = None
    default: str | None = None

@dataclass
class RncElement:
    name: str
    pattern_name: str | None = None  # The define name if applicable
    description: str | None = None
    attributes: list[RncAttribute] = field(default_factory=list)
    children: list[tuple[str, str]] = field(default_factory=list)  # (Name, Cardinality) of child elements or patterns
    content_model: str | None = None  # Textual representation of content model


class SchemaWalker:
    def __init__(self, tree: etree._ElementTree):
        self.tree = tree
        self.root = tree.getroot()
        self.defines: dict[str, etree._Element] = {}
        self.elements: dict[str, RncElement] = {}
        self.visited_patterns: set[str] = set()
        self._collect_defines()

    def _collect_defines(self) -> None:
        """Collect all named patterns (defines) in the grammar."""
        for define in self.root.xpath("//rng:define", namespaces=NAMESPACES):
            name = define.get("name")
            if name:
                self.defines[name] = define

    def walk(self) -> list[RncElement]:
        """Start traversal from the start element."""
        start_node = self.root.find("rng:start", namespaces=NAMESPACES)
        if start_node is not None:
            self._visit(start_node)
        return list(self.elements.values())

    def _get_doc(self, node: etree._Element) -> str | None:
        """Extract documentation from db:refpurpose or a:documentation."""
        # Try DocBook refpurpose
        refpurpose = node.xpath(".//db:refpurpose", namespaces=NAMESPACES)
        if refpurpose:
             # Just take the text of the first one
            return "".join(refpurpose[0].itertext()).strip()

        # Fallback to a:documentation
        doc = node.find("a:documentation", namespaces=NAMESPACES)
        if doc is not None:
             return "".join(doc.itertext()).strip()

        return None

    def _visit(self, node: etree._Element, current_element: RncElement | None = None) -> None:
        if not isinstance(node.tag, str):
            return

        tag = etree.QName(node).localname

        if tag == "element":
            name = node.get("name")
            if name and name not in self.elements:
                desc = self._get_doc(node)
                el = RncElement(name=name, description=desc)
                self.elements[name] = el

                # Check for attributes and children
                self._analyze_children(node, el)

        elif tag == "ref":
            name = node.get("name")
            if name and name not in self.visited_patterns:
                self.visited_patterns.add(name)
                if name in self.defines:
                    self._visit(self.defines[name], current_element)

        elif tag == "start":
             # Document the start element
             name = "start"
             if name not in self.elements:
                desc = self._get_doc(node)
                el = RncElement(name=name, description=desc)
                self.elements[name] = el
                self._analyze_children(node, el)

        elif tag in ("group", "choice", "interleave", "optional", "zeroOrMore", "oneOrMore", "define"):
             for child in node:
                 self._visit(child, current_element)

    def _analyze_children(self, element_node: etree._Element, rnc_element: RncElement) -> None:
        """
        Analyze the children of an element definition to find attributes, child elements,
        and build the content model string.
        """
        # 1. Collect attributes and list of child references (side-effect: populates rnc_element)
        self._collect_element_content(element_node, rnc_element)

        # 2. Build textual content model (e.g. "(foo | bar)+")
        model = self._build_content_model_str(element_node, level=0)
        if model:
            rnc_element.content_model = model

    def _build_content_model_str(self, node: etree._Element, level: int = 0) -> str | None:
        """Recursive function to build content model string, ignoring attributes."""
        tag = etree.QName(node).localname

        indent = "  " * level
        # Indent for children of this node
        sub_indent = "  " * (level + 1)
        nl = "\n"

        # Check children recursively
        children_strs = []
        for child in node:
            if child.tag is etree.Comment or child.tag is etree.ProcessingInstruction:
                 continue
            if not isinstance(child.tag, str):
                 continue

            child_tag = etree.QName(child).localname

            if child_tag == "attribute":
                continue
            elif child_tag == "element":
                name = child.get("name")
                if name:
                    children_strs.append(f"<{name}>")
                else:
                    # Recursive anonymous element
                    res = self._build_content_model_str(child, level + 1)
                    if res: children_strs.append(res)
            elif child_tag == "ref":
                children_strs.append(f"{{{child.get('name')}}}")
            elif child_tag == "text":
                children_strs.append("<text/>")
            elif child_tag == "empty":
                children_strs.append("<empty/>")
            elif child_tag == "data":
                children_strs.append(f"data({child.get('type','')})")
            elif child_tag == "value":
                children_strs.append(f'"{child.text}"')
            elif child_tag in ("group", "choice", "interleave", "optional", "zeroOrMore", "oneOrMore"):
                res = self._build_content_model_str(child, level + 1)
                if res: children_strs.append(res)

        if not children_strs:
            return None

        # Helper to decide if we need multiline
        is_complex = len(children_strs) > 1

        # Combine children based on current node type
        if tag == "optional":
            # For optional/zeroOrMore/oneOrMore, we wrap the content
            # If content is single item and simple, standard wrap.
            # If multiple items (implicitly group?), treat as group?
            # Usually parent handles group. But if <optional><a/><b/></optional>, it implies group.

            if is_complex:
                 sep = f"{nl}{sub_indent}| " # Logic check: optional with multiple children implies choice usually in DTDs but in RNG it is group unless <choice> used?
                 # RNG spec: <optional> content is a pattern. If multiple elements, it's a group.
                 sep = f",{nl}{sub_indent}"
                 inner = sep.join(children_strs)
                 return f"({nl}{sub_indent}{inner}{nl}{indent})?"
            else:
                 inner = children_strs[0]
                 # If inner is already multiline (because it was complex), wrap it nicely?
                 if nl in inner:
                     return f"{inner}?" # It already has parens?
                     # Wait, if inner is a "choice" it returns "(...)"
                     # So "((...))?"
                     # We can rely on inner return value.
                 return f"{inner}?"

        elif tag == "zeroOrMore":
            if is_complex:
                 sep = f",{nl}{sub_indent}"
                 inner = sep.join(children_strs)
                 return f"({nl}{sub_indent}{inner}{nl}{indent})*"
            else:
                 inner = children_strs[0]
                 return f"{inner}*"

        elif tag == "oneOrMore":
            if is_complex:
                 sep = f",{nl}{sub_indent}"
                 inner = sep.join(children_strs)
                 return f"({nl}{sub_indent}{inner}{nl}{indent})+"
            else:
                 inner = children_strs[0]
                 return f"{inner}+"

        elif tag == "choice":
            # ( A | B )
            sep = f"{nl}{sub_indent}| "
            inner = sep.join(children_strs)
            return f"({nl}{sub_indent}{inner}{nl}{indent})"

        elif tag == "group":
            sep = f",{nl}{sub_indent}"
            inner = sep.join(children_strs)
            return f"({nl}{sub_indent}{inner}{nl}{indent})"

        elif tag == "interleave":
            sep = f" &{nl}{sub_indent}"
            inner = sep.join(children_strs)
            return f"({nl}{sub_indent}{inner}{nl}{indent})"

        # Default (element definition or implicit sequence)
        if hasattr(node, "__iter__") and is_complex:
             sep = f",{nl}{sub_indent}"
             inner = sep.join(children_strs)
             return f"({nl}{sub_indent}{inner}{nl}{indent})"

        return children_strs[0] if children_strs else None

    def _collect_element_content(self, node: etree._Element, rnc_element: RncElement, cardinality: str = "1") -> None:
        if not hasattr(node, "iter"):
            return

        for child in node:
            # Skip comments, processing instructions, etc.
            if child.tag is etree.Comment or child.tag is etree.ProcessingInstruction:
                 continue
            if not isinstance(child.tag, str):
                 continue

            tag = etree.QName(child).localname

            if tag == "attribute":
                attr_name = child.get("name")
                if attr_name:
                    # check for optional wrapper
                    parent_tag = etree.QName(child.getparent()).localname
                    required = parent_tag != "optional"

                    desc = self._get_doc(child)
                    rnc_element.attributes.append(RncAttribute(
                        name=attr_name,
                        required=required,
                        description=desc
                    ))

            elif tag == "element":
                child_name = child.get("name")
                if child_name:
                     # For choice/optional/oneOrMore, we update cardinality
                     rnc_element.children.append((child_name, cardinality))
                # Recurse to define this child element globally
                self._visit(child)

            elif tag == "ref":
                ref_name = child.get("name")
                if ref_name:
                     rnc_element.children.append((f"Ref:{ref_name}", cardinality))
                     if ref_name not in self.visited_patterns:
                         self.visited_patterns.add(ref_name)
                         if ref_name in self.defines:
                             self._visit(self.defines[ref_name])

            elif tag == "optional":
                 # 1 -> ?
                 # + -> *
                 # * -> *
                 # ? -> ?
                 new_card = "*" if cardinality in ("*", "+") else "?"
                 self._collect_element_content(child, rnc_element, new_card)

            elif tag == "zeroOrMore":
                 # Always *
                 self._collect_element_content(child, rnc_element, "*")

            elif tag == "oneOrMore":
                 # 1 -> +
                 # ? -> *
                 # * -> *
                 # + -> +
                 new_card = "*" if cardinality in ("?", "*") else "+"
                 self._collect_element_content(child, rnc_element, new_card)

            elif tag == "choice":
                 # Items inside choice are effectively optional (unless one MUST be chosen, but which one?)
                 # Standard RELAX NG choice: (a | b).
                 # If wrapped in nothing (1), exactly one of a or b appears (1). But individually a appears 0..1, b 0..1.
                 # So effectively ? for children.
                 new_card = "*" if cardinality in ("*", "+") else "?"
                 self._collect_element_content(child, rnc_element, new_card)

            elif tag in ("group", "interleave", "define"):
                 # Recurse with same cardinality context
                 self._collect_element_content(child, rnc_element, cardinality)


