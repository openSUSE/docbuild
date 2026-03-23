
"""Sphinx extension to document RELAX NG schemas."""

from typing import Any

from sphinx.application import Sphinx

from rnc2html.builder import generate_rnc_docs
from rnc2html.directive import RncReferenceDirective


def setup(app: Sphinx) -> dict[str, Any]:
    """Register the extension with Sphinx."""
    app.add_directive("rnc-reference", RncReferenceDirective)

    # Configuration
    # List of RNC files relative to source directory
    app.add_config_value("rnc_html_files", [], "env")
    # Whether to generate separate pages for elements
    app.add_config_value("rnc_html_multi_page", False, "env")

    # Hook to generate RST files before build
    app.connect("builder-inited", generate_rnc_docs)

    return {
        "version": "0.1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
