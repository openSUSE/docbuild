"""Directive implementation for rnc-reference."""

import re
from typing import ClassVar

from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.util.docutils import SphinxDirective
from sphinx.util.logging import getLogger

from rnc2html.loader import load_schema
from rnc2html.walker import SchemaWalker

logger = getLogger(__name__)


class RncReferenceDirective(SphinxDirective):
    """Directive to insert a reference documentation from a RELAX NG schema.

    Usage:
        .. rnc-reference:: path/to/schema.rnc
    """

    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec: ClassVar = {
        "split": directives.flag,  # Future use
    }

    def run(self) -> list[nodes.Node]:
        """Run the directive."""
        schema_relpath = self.arguments[0]
        schema_path, _ = self.env.relfn2path(schema_relpath)

        try:
            tree = load_schema(schema_path)
            walker = SchemaWalker(tree)
            elements = walker.walk()
        except Exception as e:
            logger.exception("Failed to process RNC schema")
            return [
                self.state_machine.reporter.error(
                    f"RNC processing error: {e}", line=self.lineno
                )
            ]

        container = nodes.section()
        container["ids"].append(f"rnc-{schema_relpath.replace('/', '-')}")

        title = nodes.title(text=f"Schema Reference: {schema_relpath}")
        container += title

        for el in elements:
            section = nodes.section()
            section["ids"].append(f"rnc-element-{el.name}")

            # Element Title
            el_title_text = f"Element: <{el.name}>"
            section += nodes.title(text=el_title_text)

            # Description
            if el.description:
                section += nodes.paragraph(text=el.description)

            # Attributes
            if el.attributes:
                attr_section = nodes.rubric(text="Attributes")
                section += attr_section

                table = nodes.table()
                tgroup = nodes.tgroup(cols=3)
                tgroup += nodes.colspec(colwidth=30)
                tgroup += nodes.colspec(colwidth=20)
                tgroup += nodes.colspec(colwidth=50)
                table += tgroup

                thead = nodes.thead()
                row = nodes.row()
                row += nodes.entry("", nodes.paragraph(text="Name"))
                row += nodes.entry("", nodes.paragraph(text="Required?"))
                row += nodes.entry("", nodes.paragraph(text="Description"))
                thead += row
                tgroup += thead

                tbody = nodes.tbody()
                for attr in el.attributes:
                    row = nodes.row()
                    row += nodes.entry("", nodes.paragraph(text=attr.name))
                    req_text = "Yes" if attr.required else "No"
                    row += nodes.entry("", nodes.paragraph(text=req_text))
                    desc_text = attr.description or ""
                    row += nodes.entry("", nodes.paragraph(text=desc_text))
                    tbody += row
                tgroup += tbody

                section += table

            # Content Model
            if el.content_model:
                section += nodes.rubric(text="Content Model")

                # Transform content model string to RST with links
                cm_str = el.content_model

                # Replace <foo> with < :ref:`foo <rnc-element-foo>` >
                # Only match standard element names, skip <text/> etc.
                cm_str = re.sub(r"<([a-zA-Z0-9_.-]+)>", r"<:ref:`\g<1> <rnc-element-\g<1>>`>", cm_str)
                # Replace {foo} (patterns) with literal
                cm_str = re.sub(r"\{([^}]+)\}", r"{``\g<1>``}", cm_str)

                # Render using parsed-literal for verbatim block with links
                rst_lines = [".. parsed-literal::", "", f"   {cm_str}"]

                from docutils.statemachine import ViewList
                vl = ViewList(rst_lines, source="<rnc-directive>")
                self.state.nested_parse(vl, 0, section)
            container += section

        return [container]
