"""
Builder logic for multi-page generation via Sphinx hook.
"""
from pathlib import Path
from typing import List, Any

from sphinx.application import Sphinx
from sphinx.util.logging import getLogger

from rnc2html.loader import load_schema
from rnc2html.walker import SchemaWalker, RncElement

logger = getLogger(__name__)


def generate_rnc_docs(app: Sphinx) -> None:
    """
    Generate RST files for configured RNC schemas.
    Hook connected to 'builder-inited'.
    """
    files = app.config.rnc_html_files
    multi_page = app.config.rnc_html_multi_page

    if not files:
        return

    # Default output directory under source/reference/generated_rnc
    out_dir = Path(app.srcdir) / "reference" / "generated_rnc"
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
                _generate_multi_page(elements, out_dir, schema_path.stem)
            else:
                _generate_single_page(elements, out_dir, schema_path.stem)

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
        "   :widths: 20 10 70",
        "   :header-rows: 1",
        "",
        "   * - Name",
        "     - Required?",
        "     - Description",
    ]

    for attr in attributes:
        req = "Yes" if attr.required else "No"
        desc = attr.description.replace("\n", " ") if attr.description else ""
        rst.append(f"   * - ``{attr.name}``")
        rst.append(f"     - {req}")
        rst.append(f"     - {desc}")

    return "\n".join(rst) + "\n\n"

def _generate_content_model(element: RncElement) -> str:
    """Generate content model section."""
    if not element.children and not element.content_model:
        return ""

    rst = [
        "Content Model",
        "-------------",
        ""
    ]

    # 1. Show abstract model with cardinality
    if element.content_model:
        rst.append(f"**Model**: ``{element.content_model}``")
        rst.append("")

    # 2. List clickable children
    if element.children:
        rst.append("Allowed children:")
        rst.append("")

        # Deduplicate children
        for child in sorted(set(element.children)):
            # Link to other elements if they are known elements
            if child.startswith("Ref:"):
                # Clean ref name
                ref_name = child.split(":", 1)[1]
                # We link to it assuming it might be an element or a pattern we documented
                # Since we don't track pattern vs element perfectly in refs, we just link
                rst.append(f"* ``{ref_name}`` (pattern)")
            else:
                # It's an element name
                rst.append(f"* :ref:`rnc_element_{child}`")


def _generate_multi_page(elements: List[RncElement], out_dir: Path, schema_name: str) -> None:
    """Generate one RST file per element."""
    index_content = [
        _rst_title(f"{schema_name} Reference"),
        ".. toctree::",
        "   :maxdepth: 1",
        "   :glob:",
        "   :caption: Elements",
        ""
    ]

    for el in elements:
        filename = f"{el.name}.rst"
        file_path = out_dir / filename

        # Add to index
        index_content.append(f"   {el.name}")

        content = []
        # Label for cross-referencing
        content.append(f".. _rnc_element_{el.name}:\n")

        content.append(_rst_title(f"Element: <{el.name}>"))

        if el.description:
            content.append(f"{el.description}\n")

        if el.attributes:
            content.append(_rst_title("Attributes", "-"))
            content.append(_generate_attributes_table(el.attributes))

        if el.children:
            cm = _generate_content_model(el)
            if cm:
                content.append(cm)

        # Filter out None values before joining
        content = [c for c in content if c is not None]

        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(content))

    with open(out_dir / "index.rst", "w", encoding="utf-8") as f:
        f.write("\n".join(index_content))


def _generate_single_page(elements: List[RncElement], out_dir: Path, schema_name: str) -> None:
    """Generate one big RST file."""
    file_path = out_dir / f"{schema_name}.rst"

    content = []
    content.append(_rst_title(f"{schema_name} Reference"))

    for el in elements:
        content.append(f".. _rnc_element_{el.name}:\n")
        content.append(_rst_title(f"<{el.name}>", "-"))

        if el.description:
            content.append(f"{el.description}\n")

        if el.attributes:
            content.append(_generate_attributes_table(el.attributes))

        if el.children:
             content.append(_generate_content_model(el))

        content.append("\n----\n") # Separator

    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(content))
