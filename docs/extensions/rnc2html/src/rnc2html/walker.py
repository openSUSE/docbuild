"""Schema traversal and documentation extraction."""
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
    """Represents an attribute definition in the schema."""

    name: str
    required: bool = False
    description: str | None = None
    default: str | None = None
    type_info: str | None = None

@dataclass
class RncElement:
    """Represents an element definition in the schema."""

    name: str
    pattern_name: str | None = None  # The define name if applicable
    description: str | None = None
    attributes: list[RncAttribute] = field(default_factory=list)
    children: list[tuple[str, str]] = field(default_factory=list)  # (Name, Cardinality) of child elements or patterns
    content_model: str | None = None  # Textual representation of content model
    data_type: str | None = None  # Data type if element contains simple content (e.g. data, value)
    example: str | None = None  # Example code from db:example or db:screen
    example_title: str | None = None  # Title for the example from db:title


class SchemaWalker:
    """Traverses the RELAX NG schema to extract documentation."""

    def __init__(self, tree: etree._ElementTree) -> None:
        self.tree = tree
        self.root = tree.getroot()
        self.defines: dict[str, etree._Element] = {}
        # Stores list of elements because names are not unique (different patterns can define same element name)
        self.elements: list[RncElement] = []
        self.visited_patterns: set[str] = set()
        self.expanding_refs: set[str] = set()
        self._collect_defines()

    def _collect_defines(self) -> None:
        """Collect all named patterns (defines) in the grammar."""
        for define in self.root.xpath("//rng:define", namespaces=NAMESPACES):
            name = define.get("name")
            if name:
                self.defines[name] = define


    def _is_attribute_def(self, ref_name: str) -> bool:
        """Check if the referenced define contains attributes, possibly nested, but NO content."""
        if ref_name not in self.defines:
            return False
        node = self.defines[ref_name]
        # It is an attribute definition only if it has attributes AND has no elements/text
        return self._node_has_attribute(node) and not self._node_has_content(node)

    def _node_has_content(self, node: etree._Element, visited: set[str] | None = None) -> bool:  # noqa: C901
        """Recursive check for content elements (element, text, data, etc.)."""
        if visited is None:
            visited = set()

        tag = etree.QName(node).localname
        if tag in ("element", "text", "data", "value", "empty"):
            return True
        if tag == "attribute":
            return False

        if tag == "ref":
            ref_name = node.get("name")
            if ref_name:
                if self._resolve_ref_to_element(ref_name):
                     return True

                if ref_name in self.defines and ref_name not in visited:
                    visited.add(ref_name)
                    if self._node_has_content(self.defines[ref_name], visited):
                        return True

        for child in node:
            if not isinstance(child.tag, str):
                continue
            if self._node_has_content(child, visited):
                return True
        return False

    def _node_has_attribute(self, node: etree._Element, visited: set[str] | None = None) -> bool:  # noqa: C901
        """Recursive check for attribute, stopping at element boundaries."""
        if visited is None:
            visited = set()

        tag = etree.QName(node).localname
        tag = etree.QName(node).localname
        if tag == "attribute":
            return True
        if tag == "element":
            return False

        # If we see a ref, we must check if that ref resolves to attributes
        # UNLESS the ref resolves to an element (because elements are handled via _resolve_ref_to_element logic)
        # But _node_has_attribute is purely checking "does this node PROVIDE attributes to its parent?"

        if tag == "ref":
            ref_name = node.get("name")
            if ref_name:
                # If the ref points to an element definition, it DOES NOT provide attributes
                if self._resolve_ref_to_element(ref_name):
                     return False

                if ref_name in self.defines and ref_name not in visited:
                    visited.add(ref_name)
                    if self._node_has_attribute(self.defines[ref_name], visited):
                        return True

        for child in node:
            if not isinstance(child.tag, str):
                continue
            if self._node_has_attribute(child, visited):
                return True
        return False

        for child in node:
            if not isinstance(child.tag, str):
                continue
            if self._node_has_attribute(child, visited):
                print(f"DEBUG: Child {etree.QName(child).localname} of {tag} returned True!")
                return True
        return False

    def _resolve_ref_to_element(self, ref_name: str) -> str | None:
        """If a reference points to a define containing exactly one element.

        return that element's name.
        """
        if ref_name not in self.defines:
            return None

        define = self.defines[ref_name]
        found_element = None

        for child in define:
            if not isinstance(child.tag, str):
                continue

            qname = etree.QName(child)
            # Skip documentation/annotations
            if qname.namespace in (A_NS, DOCBOOK_NS):
                continue

            if found_element is not None:
                # More than one meaningful child
                return None

            if qname.localname == "element":
                found_element = child.get("name")
            else:
                # Contains something other than an element (e.g. group, optional, text)
                return None

        return found_element

    def _expand_ref_to_content(self, ref_name: str, level: int) -> str | None:
        """If a ref points to a define that is just a group/choice of elements.

        expand it inline rather than showing {patternName}.
        Used for things like ds.htmlblock which is a choice of p, div, pre, etc.
        """
        if ref_name not in self.defines:
            return None

        # Avoid infinite recursion
        if ref_name in self.expanding_refs:
            return f"{{``{ref_name}``}}"

        self.expanding_refs.add(ref_name)
        try:
            define_node = self.defines[ref_name]
            return self._build_content_model_str(define_node, level)
        finally:
            self.expanding_refs.remove(ref_name)

    def walk(self) -> list[RncElement]:
        """Start traversal from the start element."""
        start_node = self.root.find("rng:start", namespaces=NAMESPACES)
        if start_node is not None:
            self._visit(start_node)
        return self.elements

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

    def _get_example(self, node: etree._Element) -> tuple[str | None, str | None]:
        """Extract example code and title.

        Returns: (example_code, example_title)
        """
        # First, check inside the node itself for <db:example>
        example_node = node.find(".//db:example", namespaces=NAMESPACES)
        if example_node is not None:
             screen = example_node.find("db:screen", namespaces=NAMESPACES)
             title_node = example_node.find("db:title", namespaces=NAMESPACES)
             title = "".join(title_node.itertext()).strip() if title_node is not None else None

             if screen is not None and screen.text:
                 return (screen.text.strip(), title)

        # Check for <db:screen> directly
        screen_node = node.find(".//db:screen", namespaces=NAMESPACES)
        if screen_node is not None and screen_node.text:
            return (screen_node.text.strip(), None)

        return (None, None)

    def _visit(self, node: etree._Element, current_element: RncElement | None = None, current_pattern: str | None = None) -> None:  # noqa: C901
        if not isinstance(node.tag, str):
            return

        tag = etree.QName(node).localname

        if tag == "element":
            name = node.get("name")
            if name:
                desc = self._get_doc(node)
                # Find example
                example, example_title = self._get_example(node)

                # If not found directly, look at parent define's siblings (the <div> logic)
                if not example:
                     parent = node.getparent()
                     if parent is not None and etree.QName(parent).localname == "define":
                         grandparent = parent.getparent()
                         if grandparent is not None:
                             # Search grandparent's children
                             for child in grandparent:
                                 if not isinstance(child.tag, str):
                                     continue
                                 child_qname = etree.QName(child)

                                 if child_qname.namespace == DOCBOOK_NS:
                                     if child_qname.localname == "example":
                                         screen = child.find("db:screen", namespaces=NAMESPACES)
                                         title_node = child.find("db:title", namespaces=NAMESPACES)

                                         if screen is not None and screen.text:
                                             example = screen.text.strip()
                                             if title_node is not None:
                                                 example_title = "".join(title_node.itertext()).strip()
                                             break

                                     elif child_qname.localname == "screen" and child.text:
                                         example = child.text.strip()
                                         break

                el = RncElement(
                    name=name,
                    pattern_name=current_pattern,
                    description=desc,
                    example=example,
                    example_title=example_title
                )
                self.elements.append(el)

                # Check for attributes and children
                self._analyze_children(node, el)

        elif tag == "ref":
            name = node.get("name")
            if name and name not in self.visited_patterns:
                self.visited_patterns.add(name)
                if name in self.defines:
                    # Switch to the define node, treating 'name' as current pattern for children
                    self._visit(self.defines[name], current_element, current_pattern=name)

        elif tag == "start":
             # Document the start element
             name = "start"
             # Avoid re-adding start if visited (though start is usually unique)
             if not any(e.name == "start" for e in self.elements):
                desc = self._get_doc(node)
                el = RncElement(name=name, description=desc)
                self.elements.append(el)
                self._analyze_children(node, el)

        elif tag == "define":
             pattern_name = node.get("name")
             for child in node:
                 self._visit(child, current_element, current_pattern=pattern_name)

        elif tag in ("group", "choice", "interleave", "optional", "zeroOrMore", "oneOrMore"):
             for child in node:
                 self._visit(child, current_element, current_pattern=current_pattern)

    def _analyze_children(self, element_node: etree._Element, rnc_element: RncElement) -> None:
        """Analyze the children of an element definition to find attributes, child elements.

        Build the content model string.
        """
        # 1. Collect attributes and list of child references (side-effect: populates rnc_element)
        self._collect_element_content(element_node, rnc_element)

        # 2. Build textual content model (e.g. "(foo | bar)+")
        model = self._build_content_model_str(element_node, level=0)
        if model:
            rnc_element.content_model = model

        # 3. Infer simple data type if applicable
        rnc_element.data_type = self._get_simple_content_type(element_node)

    def _get_simple_content_type(self, node: etree._Element, visited: set[str] | None = None) -> str | None:  # noqa: C901
        """Check if the node defines a simple data type (data, value, or enum) and return its description.

        Returns None if the content is complex (elements, mixed, etc).
        """
        if visited is None:
            visited = set()

        for child in node:
            if not isinstance(child.tag, str):
                continue
            tag = etree.QName(child).localname

            if tag in ("attribute", "documentation", "refpurpose", "example", "param"):
                continue

            if tag == "data":
                return self._get_attribute_type(node) # Reuse logic which handles data/params

            if tag == "choice":
                 # Check if it looks like an enum (choice of values)
                 type_info = self._get_attribute_type(node)
                 if type_info and "Enum" in type_info:
                     return type_info
                 # Otherwise drill down?
                 # If it is Choice of Refs to Data?
                 pass

            if tag == "value":
                if child.text:
                    return f"Value: {child.text}"

            if tag == "ref":
                ref_name = child.get("name")
                if ref_name:
                    if self._is_attribute_def(ref_name):
                         continue

                    if self._resolve_ref_to_element(ref_name):
                        # Points to element -> Complex
                        return None

                    if ref_name in self.defines and ref_name not in visited:
                        visited.add(ref_name)
                        # We recurse into the definition
                        # Logic: if the definition returns a type, we take it.
                        res = self._get_simple_content_type(self.defines[ref_name], visited)
                        if res:
                            return res

            if tag in ("group", "interleave", "optional", "zeroOrMore", "oneOrMore"):
                res = self._get_simple_content_type(child, visited)
                if res:
                    return res

            if tag in ("element", "text", "empty"):
                return None

        return None


    def _dedent(self, text: str) -> str:
        """Dedent a multiline string by 2 spaces (ignoring first line)."""
        if "\n" not in text:
            return text
        lines = text.split("\n")
        new_lines = [lines[0]]
        for line in lines[1:]:
            if line.startswith("  "):
                new_lines.append(line[2:])
            else:
                new_lines.append(line)
        return "\n".join(new_lines)

    def _quantify(self, text: str, op: str) -> str:
        """Apply quantifier, escaping the operator if necessary (e.g. after backticks)."""
        # If text ends with backticks (inline literal) or a closing delimiter that creates ambiguity,
        # we must escape the quantifier asterisk/plus/opt to prevent RST parsing errors.
        # Specifically "Inline literal start-string without end-string".
        if text.strip().endswith("``"):
             return f"{text}\\{op}"
        return f"{text}{op}"

    def _build_content_model_str(self, node: etree._Element, level: int = 0) -> str | None:  # noqa: C901
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
                    if res:

                        children_strs.append(res)
            elif child_tag == "ref":
                ref_name = child.get('name')
                if ref_name:
                    if self._is_attribute_def(ref_name):
                         continue

                    resolved = self._resolve_ref_to_element(ref_name)
                    if resolved:
                        children_strs.append(f"<{resolved}>")
                    else:
                        # If a pattern ref does not resolve to a SINGLE element,
                        # it might be a choice/group of elements (like ds.htmlblock).
                        # We should try to expand it if it's purely content.
                        expanded = self._expand_ref_to_content(ref_name, level)
                        if expanded:
                            children_strs.append(expanded)
                        else:
                            children_strs.append(f"{{{ref_name}}}")
            elif child_tag == "text":
                children_strs.append("``text``")
            elif child_tag == "empty":
                children_strs.append("``empty``")
            elif child_tag == "data":
                children_strs.append(f"data({child.get('type','')})")
            elif child_tag == "value":
                children_strs.append(f'"{child.text}"')
            elif child_tag in ("group", "choice", "interleave", "optional", "zeroOrMore", "oneOrMore"):
                res = self._build_content_model_str(child, level + 1)
                if res:

                    children_strs.append(res)

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
                 return self._quantify(self._dedent(inner), "?")

        elif tag == "zeroOrMore":
            if is_complex:
                 sep = f",{nl}{sub_indent}"
                 inner = sep.join(children_strs)
                 return f"({nl}{sub_indent}{inner}{nl}{indent})*"
            else:
                 inner = children_strs[0]
                 return self._quantify(self._dedent(inner), "*")

        elif tag == "oneOrMore":
            if is_complex:
                 sep = f",{nl}{sub_indent}"
                 inner = sep.join(children_strs)
                 return f"({nl}{sub_indent}{inner}{nl}{indent})+"
            else:
                 inner = children_strs[0]
                 return self._quantify(self._dedent(inner), "+")

        elif tag == "choice":
            if not is_complex:
                 return self._dedent(children_strs[0])
            sep = f"{nl}{sub_indent}| "
            inner = sep.join(children_strs)
            return f"({nl}{sub_indent}{inner}{nl}{indent})"

        elif tag == "group":
            if not is_complex:
                 return self._dedent(children_strs[0])
            sep = f",{nl}{sub_indent}"
            inner = sep.join(children_strs)
            return f"({nl}{sub_indent}{inner}{nl}{indent})"

        elif tag == "interleave":
            if not is_complex:
                 return self._dedent(children_strs[0])
            sep = f" &{nl}{sub_indent}"
            inner = sep.join(children_strs)
            return f"({nl}{sub_indent}{inner}{nl}{indent})"

        # Default (element definition or implicit sequence)
        if hasattr(node, "__iter__") and is_complex:
             sep = f",{nl}{sub_indent}"
             inner = sep.join(children_strs)
             return f"({nl}{sub_indent}{inner}{nl}{indent})"

        return self._dedent(children_strs[0]) if children_strs else None

    def _collect_element_content(self, node: etree._Element, rnc_element: RncElement, cardinality: str = "1") -> None:  # noqa: C901
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
                    # Also consider inherited cardinality
                    inherited_optional = cardinality in ("?", "*")
                    is_optional = (parent_tag == "optional") or inherited_optional

                    desc = self._get_doc(child)
                    default_val = child.get(f"{{{A_NS}}}defaultValue")
                    type_info = self._get_attribute_type(child)

                    rnc_element.attributes.append(RncAttribute(
                        name=attr_name,
                        required=not is_optional,
                        description=desc,
                        default=default_val,
                        type_info=type_info
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
                     if self._is_attribute_def(ref_name):
                         # If this ref points to attributes, inline them into the current element's attributes
                         if ref_name in self.defines:
                             # Recurse into the definition to extract attributes
                             # Use the same cardinality context
                             self._collect_element_content(self.defines[ref_name], rnc_element, cardinality)
                     else:
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
                 # + -> +
                 # * -> *
                 # ? -> * (optional repeated -> *)
                 new_card = "+" if cardinality in ("1", "+") else "*"
                 self._collect_element_content(child, rnc_element, new_card)

            elif tag == "choice":
                 # Choice doesn't change cardinality directly for children unless specific
                 # But in content model it's (A|B).
                 # We just pass through cardinality.
                 self._collect_element_content(child, rnc_element, cardinality)

            elif tag in ("group", "interleave", "define"):
                 self._collect_element_content(child, rnc_element, cardinality)

    def _get_attribute_type(self, node: etree._Element, visited: set[str] | None = None) -> str | None:  # noqa: C901
        """Extract type information (data type, enum values) from an attribute definition."""
        if visited is None:
            visited = set()

        # Check for <data type="...">
        data_node = node.find("rng:data", namespaces=NAMESPACES)
        if data_node is not None:
            type_name = data_node.get("type", "string")
            params = []
            for param in data_node.findall("rng:param", namespaces=NAMESPACES):
                p_name = param.get("name")
                if param.text:
                    params.append(f"{p_name}: {param.text}")

            result = type_name
            if params:
                result += f" ({', '.join(params)})"
            return result

        # Check for <choice> (enum)
        choice_node = node.find("rng:choice", namespaces=NAMESPACES)
        if choice_node is not None:
             values = []
             for val in choice_node.findall("rng:value", namespaces=NAMESPACES):
                 if val.text:
                     values.append(val.text)

             if values:
                 return f"Enum: {', '.join(values)}"

        # Check for <ref> (reference to type definition)
        ref_node = node.find("rng:ref", namespaces=NAMESPACES)
        if ref_node is not None:
            ref_name = ref_node.get("name")
            if ref_name and ref_name not in visited:
                visited.add(ref_name)
                if ref_name in self.defines:
                    return self._get_attribute_type(self.defines[ref_name], visited)

        return None




