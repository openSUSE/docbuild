"""
Builder logic for multi-page generation via Sphinx hook.
"""
import re
from pathlib import Path
from typing import Any

from sphinx.application import Sphinx
from sphinx.util.logging import getLogger

from rnc2html.loader import load_schema
from rnc2html.walker import SchemaWalker, RncElement, RncAttribute

logger = getLogger(__name__)


def generate_rnc_docs(app: Sphinx) -> None:
    """
    Generate RST files for configured RNC schemas.
    Hook connected to 'builder-inited'.
    """
    files = app.config.rnc_html_files
    multi_page = app.config.rnc_html_multi_page
    gen_element_index = app.config.rnc_html_gen_element_index
    gen_attribute_index = app.config.rnc_html_gen_attribute_index

    if not files:
        return

    # Default output directory under source/reference/portal
    out_dir = Path(app.srcdir) / "reference" / "portal"
    out_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"[rnc2html] Generating documentation for {len(files)} schemas in {out_dir}")

    for relative_path in files:
        schema_path = Path(app.srcdir) / relative_path
        if not schema_path.exists():
            logger.warning(f"[rnc2html] Schema file not found: {schema_path}")
            continue

        try:
            tree = load_schema(schema_path)
            walker = SchemaWalker(tree)
            elements = walker.walk()

            if multi_page:
                generate_multi_page(elements, out_dir, schema_path.stem, gen_element_index, gen_attribute_index)
            else:
                generate_single_page(elements, out_dir, schema_path.stem)

        except Exception:
            logger.exception(f"[rnc2html] Failed to generate docs for {schema_path}")


def _rst_title(text: str, char: str = "=") -> str:
    return f"{text}\n{char * len(text)}\n"


def _generate_attributes_table(attributes: list) -> str:
    """Generate a list-table for attributes."""
    if not attributes:
        return ""

    rst = [
        ".. list-table:: Attributes",
        "   :widths: 20 15 10 10 45",
        "   :header-rows: 1",
        "",
        "   * - Name",
        "     - Type",
        "     - Required?",
        "     - Default",
        "     - Description",
    ]

    for attr in attributes:
        req = "Yes" if attr.required else "No"
        desc = attr.description.replace("\n", " ") if attr.description else ""
        default_val = f"``{attr.default}``" if attr.default else "n/a"
        type_info = f"``{attr.type_info}``" if attr.type_info else "string"

        rst.append(f"   * - ``{attr.name}``")
        rst.append(f"     - {type_info}")
        rst.append(f"     - {req}")
        rst.append(f"     - {default_val}")
        rst.append(f"     - {desc}")

    return "\n".join(rst) + "\n\n"

def _generate_content_model(element: RncElement) -> str:
    """Generate content model section."""
    if not element.content_model:
        return ""

    rst = [
        "Content Model",
        "-------------",
        "",
        ".. parsed-literal::",
        ""
    ]

    cm_str = element.content_model
    # Replace <foo> with < :ref:`foo <rnc_element_foo>` >
    # This puts brackets distinct from the link text to help RST parser.
    # Updated regex to include colons for namespaced elements (e.g. xi:include)
    cm_str = re.sub(r"<([a-zA-Z0-9_:.-]+)>", r"<:ref:`\g<1> <rnc_element_\g<1>>`>", cm_str)

    # Replace {foo} with {``foo``} (pattern ref)
    cm_str = re.sub(r"\{([^}]+)\}", r"{``\g<1>``}", cm_str)

    # Indent every line for the parsed-literal block
    indented_cm = "\n".join("   " + line for line in cm_str.splitlines())
    rst.append(indented_cm)
    rst.append("")

    return "\n".join(rst)


def _generate_element_index(elements_files: list[tuple[RncElement, str]]) -> str:
    """Generate sorted list of elements."""
    sorted_elements = sorted(elements_files, key=lambda x: x[0].name.lower())

    rst = [
        _rst_title("Element Index"),
        ""
    ]

    current_char = None

    for el, filename in sorted_elements:
        first_char = el.name[0].upper()
        if first_char != current_char:
            if current_char is not None:
                rst.append("")
            rst.append(f"{first_char}")
            rst.append("-")
            rst.append("")
            current_char = first_char

        display_name = f"<{el.name}>"
        if el.pattern_name:
            display_name += f" ({el.pattern_name})"

        rst.append(f"* :doc:`{display_name} <{filename}>`")

    return "\n".join(rst)


def _generate_attribute_index(elements_files: list[tuple[RncElement, str]]) -> str:
    """Generate index of attributes."""
    # Attribute Name -> List of (Element Display Name, Filename)
    attr_map: dict[str, list[tuple[str, str]]] = {}

    for el, filename in elements_files:
        display_element = f"<{el.name}>"
        if el.pattern_name:
             display_element += f" ({el.pattern_name})"

        for attr in el.attributes:
             link = (display_element, filename)
             if attr.name not in attr_map:
                 attr_map[attr.name] = []
             attr_map[attr.name].append(link)

    sorted_attrs = sorted(attr_map.keys())

    rst = [
        _rst_title("Attribute Index"),
        ""
    ]

    current_char = None
    for attr_name in sorted_attrs:
        clean_name = attr_name.lstrip("@")
        first_char = clean_name[0].upper() if clean_name else '?'
        if first_char != current_char:
            if current_char is not None:
                 rst.append("")
            rst.append(f"{first_char}")
            rst.append("-")
            rst.append("")
            current_char = first_char

        rst.append(f"* ``{attr_name}``")
        # List elements
        # Sort usages by element name
        usages = sorted(attr_map[attr_name], key=lambda x: x[0].lower())
        for (el_display, filename) in usages:
            rst.append(f"  - :doc:`{el_display} <{filename}>`")

    return "\n".join(rst)


def generate_multi_page(elements: list[RncElement], out_dir: Path, schema_name: str,
                        gen_element_index: bool = False, gen_attribute_index: bool = False) -> None:
    """Generate one RST file per element."""
    index_content = [
        _rst_title(f"{schema_name} Reference"),
        ".. toctree::",
        "   :maxdepth: 1",
        "   :glob:",
        "   :caption: Elements",
        ""
    ]

    # Track generated filenames to handle duplicates
    generated_files = set()
    # Track element -> filename mapping for indices
    elements_files: list[tuple[RncElement, str]] = []

    # Track element names for canonical labels
    labeled_names = set()

    for el in elements:
        # Determine filename
        filename = f"{el.name}"
        if el.pattern_name and (filename in generated_files or any(e.name == el.name and e is not el for e in elements)):
            # Disambiguate with pattern name
             filename = f"{el.name}-{el.pattern_name}"

        # Ensure uniqueness if pattern name isn't enough (unlikely but safe)
        base_filename = filename
        counter = 1
        while filename in generated_files:
             filename = f"{base_filename}-{counter}"
             counter += 1

        generated_files.add(filename)
        elements_files.append((el, filename))

        file_path = out_dir / f"{filename}.rst"

        # Add to index
        index_content.append(f"   {filename}")

        content = []
        # Labels for cross-referencing
        # 1. Canonical label (rnc_element_name) - for first occurrence
        # 2. Specific label (rnc_element_name_pattern) - always if different

        canonical_label = f"rnc_element_{el.name}"
        label_suffix = f"_{el.pattern_name}" if el.pattern_name else ""
        specific_label = f"rnc_element_{el.name}{label_suffix}"

        if el.name not in labeled_names:
            content.append(f".. _{canonical_label}:\n")
            labeled_names.add(el.name)

        if specific_label != canonical_label:
            content.append(f".. _{specific_label}:\n")

        if el.name == "start":
            content.append(_rst_title("Start"))
        else:
             title = f"Element: <{el.name}>"
             if el.pattern_name:
                 title += f" ({el.pattern_name})"
             content.append(_rst_title(title))

        if el.description:
            content.append(f"{el.description}\n")

        if el.example:
            content.append(_rst_title("Example", "-"))
            content.append(".. code-block:: xml")
            if el.example_title:
                content.append(f"   :caption: {el.example_title}")
            content.append("")
            # Indent example code
            for line in el.example.splitlines():
                content.append(f"   {line}")
            content.append("")

        if el.attributes:
            content.append(_rst_title("Attributes", "-"))
            content.append(_generate_attributes_table(el.attributes))

        if el.content_model:
            cm = _generate_content_model(el)
            if cm:
                content.append(cm)

        # Filter out None values before joining
        content = [c for c in content if c is not None]

        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(content))

    # Generate Indices if requested
    indices_toctree = []

    if gen_element_index:
        idx_content = _generate_element_index(elements_files)
        with open(out_dir / "genindex-elements.rst", "w", encoding="utf-8") as f:
            f.write(idx_content)
        indices_toctree.append("genindex-elements")

    if gen_attribute_index:
        idx_content = _generate_attribute_index(elements_files)
        with open(out_dir / "genindex-attributes.rst", "w", encoding="utf-8") as f:
            f.write(idx_content)
        indices_toctree.append("genindex-attributes")

    if indices_toctree:
        index_content.append("")
        index_content.append(".. toctree::")
        index_content.append("   :maxdepth: 1")
        index_content.append("   :caption: Indices")
        index_content.append("")
        for idx in indices_toctree:
            index_content.append(f"   {idx}")

    with open(out_dir / "index.rst", "w", encoding="utf-8") as f:
        f.write("\n".join(index_content))

    logger.info(f"[rnc2html] Generated {len(generated_files)} RST files for schema '{schema_name}'")


def generate_single_page(elements: list[RncElement], out_dir: Path, schema_name: str) -> None:
    """Generate one big RST file."""
    file_path = out_dir / f"{schema_name}.rst"

    content = []
    content.append(_rst_title(f"{schema_name} Reference"))

    # Need to handle duplicate names to ensure labels are unique
    counts = {}
    labeled_names = set()

    for el in elements:
        # Create a unique-ish label.
        # If pattern name exists, use it.
        label_suffix = f"_{el.pattern_name}" if el.pattern_name else ""
        if not label_suffix:
            # Fallback for duplicates without pattern name (unlikely for top-level defines)
            num = counts.get(el.name, 0) + 1
            counts[el.name] = num
            if num > 1:
                label_suffix = f"_{num}"

        canonical_label = f"rnc_element_{el.name}"
        specific_label = f"rnc_element_{el.name}{label_suffix}"

        if el.name not in labeled_names:
            content.append(f".. _{canonical_label}:\n")
            labeled_names.add(el.name)

        if specific_label != canonical_label:
            content.append(f".. _{specific_label}:\n")

        if el.name == "start":
            content.append(_rst_title("Start", "-"))
        else:
            title = f"<{el.name}>"
            if el.pattern_name:
                title += f" ({el.pattern_name})"
            content.append(_rst_title(title, "-"))

        if el.description:
            content.append(f"{el.description}\n")

        if el.attributes:
            content.append(_generate_attributes_table(el.attributes))

        if el.content_model:
             content.append(_generate_content_model(el))

        content.append("\n----\n") # Separator

    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(content))
