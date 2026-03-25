"""Configuration file for the Sphinx documentation builder."""
# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

from pathlib import Path
import sys

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

"""Configuration file for the Sphinx documentation builder."""

project = 'rnc2html'
copyright = '2026, SUSE'  # noqa: A001
author = 'SUSE'
release = '0.1.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

# Add extension source to path
# We are in docs/extensions/rnc2html/docs/
# Extension source is in docs/extensions/rnc2html/src
EXTENSION_ROOT = Path(__file__).parents[1] / "src"
sys.path.insert(0, str(EXTENSION_ROOT.resolve()))

extensions = [
    "rnc2html",
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']

# -- rnc2html options --------------------------------------------------------

rnc_html_files = [
    # "book.rng",
    "portal-config-schema.rng",
]
rnc_html_multi_page = True
rnc_html_gen_element_index = True
rnc_html_gen_attribute_index = True
