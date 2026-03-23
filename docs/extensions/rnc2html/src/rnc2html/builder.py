"""
Builder logic for multi-page generation via Sphinx hook.
"""
import re
from pathlib import Path
from typing import Any

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
                generate_multi_page(elements, out_dir, schema_path.stem)
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
    cm_str = re.sub(r"<([a-zA-Z0-9_.-]+)>", r"<:ref:`\g<1> <rnc_element_\g<1>>`>", cm_str)

    # Replace {foo} with {``foo``} (pattern ref)
    cm_str = re.sub(r"\{([^}]+)\}", r"{``\g<1>``}", cm_str)

    # Indent every line for the parsed-literal block
    indented_cm = "\n".join("   " + line for line in cm_str.splitlines())
    rst.append(indented_cm)
    rst.append("")

    return "\n".join(rst)



def generate_multi_page(elements: list[RncElement], out_dir: Path, schema_name: str) -> None:
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


def generate_single_page(elements: list[RncElement], out_dir: Path, schema_name: str) -> None:
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
