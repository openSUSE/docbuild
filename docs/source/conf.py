"""Configuration file for the Sphinx documentation builder."""
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

from datetime import datetime
from pathlib import Path
import sys

from sphinx.application import Sphinx
from sphinx.errors import ExtensionError
from sphinx.util import logging

from docbuild.__about__ import __version__

# Add the directory containing toml_parser.py to sys.path
# If it's in the same directory as conf.py:
sys.path.insert(0, str(Path(__file__).parent))

project = "docbuild"
current_year = datetime.now().year
copyright = f"{current_year}, Tom Schraitle | Sushant Gaurav"  # noqa: A001
author = "Tom Schraitle, Sushant Gaurav"
release = __version__

gh_user = "openSUSE"
gh_repo_url = f"https://github.com/{gh_user}/{project}"
gh_repo_slug = f"{gh_user}/{project}"

xml_config_repo = "https://gitlab.suse.de/susedoc/docserv-config"
xml_config_slug = "/".join(xml_config_repo.rsplit("/", 2)[-2:])

# --- Prolog configuration
rst_prolog = f"""
.. |daps| replace:: :command:`daps`
.. |project| replace:: {project}
.. |gh_repo_slug| replace:: {gh_repo_slug}
.. |github_user| replace:: {gh_user}
.. |gh_repo| replace:: {gh_repo_url}
.. |gh_repo_url| replace:: `{gh_repo_slug} <{gh_repo_url}>`__
.. |uv| replace:: :command:`uv`
.. |gh_release| replace:: `Releases <{gh_repo_url}/releases/>`__
.. |gl_xmlconfig| replace:: `GL://{xml_config_slug} <{xml_config_repo}>`__
"""

# -- General configuration
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    # Include documentation from docstrings
    # https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html
    "sphinx.ext.autodoc",
    #
    # Link to other projects' documentation
    # https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html
    "sphinx.ext.intersphinx",
    #
    # Test code snippets in the documentation
    # https://www.sphinx-doc.org/en/master/usage/extensions/doctest.html
    "sphinx.ext.doctest",
    #
    # Create short aliases for external links
    # https://www.sphinx-doc.org/en/master/usage/extensions/extlinks.html
    "sphinx.ext.extlinks",
    #
    # Embed Graphviz graphs
    # https://www.sphinx-doc.org/en/master/usage/extensions/graphviz.html
    "sphinx.ext.graphviz",
    #
    # Document Click command-line interfaces
    # https://sphinx-click.readthedocs.io/en/latest/
    "sphinx_click",
    #
    # Add a "copy" button to code blocks
    # https://sphinx-copybutton.readthedocs.io/en/latest/
    "sphinx_copybutton",
    #
    # Render type hints in signatures
    # https://github.com/tox-dev/sphinx-autodoc-typehints
    "sphinx_autodoc_typehints",
    #
    # Generate API documentation from source code
    # https://sphinx-autoapi.readthedocs.io/en/latest/
    "autoapi.extension",
]

templates_path = ["_templates"]
exclude_patterns = []

language = "en"

# -- Options for autoapi extension
# https://sphinx-autoapi.readthedocs.io/en/latest/reference/config.html
autoapi_modules = {
    "docbuild": None,
    # {
    #     # "output": "reference/_autoapi",
    #     # "prune": True|False,
    #     # "override": True|False,
    #     # "template":
    # }
}
autoapi_root = "reference/_autoapi"
autoapi_dirs = ["../../src/"]
autoapi_type = "python"
autoapi_add_toctree_entry = False
# autoapi_template_dir = "_templates/autoapi"
autoapi_options = [
    "members",
    # "undoc-members",
    # 'inherited-members',
    "show-inheritance",
    "show-module-summary",
    # 'imported-members',
    "special-members",
    "show-inheritance-diagram",  # needs sphinx.ext.inheritance_diagram & graphviz
    # "private-members",
]
autoapi_keep_files = True
autodoc_typehints = "signature"
autoapi_own_page_level = "class"
# autoapi_python_use_implicit_namespaces = True

# -- Options for extlinks extension ------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/extlinks.html
extlinks = {
    # Example for linking to a specific file/path in the repo:
    "gh_path": (f"{gh_repo_url}/blob/main/%s", "%s"),
    # Example for linking to a specific directory in the repo:
    "gh_tree": (f"{gh_repo_url}/tree/main/%s", "%s"),
    # Linking to the GH issue tracker:
    "gh": (f"{gh_repo_url}/issues/%s", "GH #%s"),
}


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output


autosummary_generate = False
autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "show-inheritance": True,
    "inherited-members": False,
    "private-members": True,
}

html_theme = "pydata_sphinx_theme"
# html_theme = "alabaster"

html_static_path = ["_static"]

html_css_files = [
    "css/custom.css",
]

html_context = {
    "github_user": gh_user,
    "github_repo": project,
    "github_version": "main",
    "doc_path": "docs/source/",
}

html_theme_options = {
    "announcement": "Documentation is under construction.",
    "show_prev_next": True,
    # "html_last_updated_fmt": "%b %d, %Y",
    "content_footer_items": ["last-updated"],
    "github_url": gh_repo_url,
    #   "external_links": [
    #       {"name": "link-one-name", "url": "https://<link-one>"},
    #   ],
    #
    "icon_links": [
        {
            "name": "GitLab susedoc/docserv-config",
            "url": xml_config_repo,
            "icon": "fa-brands fa-square-gitlab",
            "type": "fontawesome",
        },
        {
            "name": "Kanban board",
            "url": "https://github.com/orgs/openSUSE/projects/27/",
            "icon": "fa-solid fa-table-columns",
            "type": "fontawesome",
        },
    ],
    #
    "use_edit_page_button": True,
    "back_to_top_button": True,
    "logo": {
        "text": "Docbuild Documentation",
        # "image_light": "_static/logo-light.png",
        # "image_dark": "_static/logo-dark.png",
    },
}

html_logo = "_static/logo.png"

html_favicon = "_static/favicon.ico"

# -- Options for intersphinx extension ---------------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html#configuration

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "pydantic": ("https://docs.pydantic.dev/latest/", None),
    "click": ("https://click.palletsprojects.com/en/latest/", None),
    "jinja2": ("https://jinja.palletsprojects.com/en/latest/", None),
}

# -- Options for linkcheck builder --------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-the-linkcheck-builder

linkcheck_ignore = [
    # Ignore links to the internal GitLab server, which may require a VPN or login.
    r"https://gitlab\.suse\.de/.*",
    # Ignore links to local development servers.
    r"http://127\.0\.0\.1:\d+/",
    r"http://localhost:\d+/",
    # Ignore mailto links
    r"mailto:.*",
    # Ignore settings page as only admins have access
    rf"https://github\.com/{gh_user}/{project}/settings/rules",
    # Just ignore useless example URLs
    r"https://github\.com/org/repo",
]


# Configuration for TOML documentation generation
# Format: (input_toml, output, {additional_config})
# Paths are relative to the conf.py directory
toml_doc_config = [
    # 1
    (
        "../../etc/docbuild/env.example.toml",
        "reference/env-toml/env-toml-ref.rst.inc",
        {},  # Use default prefix, no need to add that.
    ),
]

logger = logging.getLogger(__name__)


def run_toml_generator(app: Sphinx) -> None:
    """Run the TOML documentation generator before the build process starts."""
    from toml_parser import generate_toml_reference

    conf_dir = Path(app.confdir)
    for input_rel, output_rel, config_data in toml_doc_config:
        toml_input = (conf_dir / input_rel).resolve()
        rst_output = (conf_dir / output_rel).resolve()

        # Check if the input file exists before proceeding
        if not toml_input.exists():
            msg = (
                "TOML documentation generation failed: "
                f"Input file not found at {toml_input}"
            )
            logger.error(msg)
            raise ExtensionError(msg)

        # Optimization: Only generate if input is newer than output
        if rst_output.exists():
            input_mtime = toml_input.stat().st_mtime
            output_mtime = rst_output.stat().st_mtime

            if input_mtime <= output_mtime:
                logger.info(
                    "Skipping TOML reference generation: %s is up to date.",
                    rst_output.name,
                )
                continue

        # Ensure the directory exists
        rst_output.parent.mkdir(parents=True, exist_ok=True)

        logger.info(
            "Generating TOML reference: %s -> %s", toml_input.name, rst_output.name
        )
        generate_toml_reference(toml_input, rst_output, **config_data)


def setup(app: Sphinx) -> None:
    """Sphinx setup function to connect the TOML generator to the build process."""
    # This hook ensures the file exists before Sphinx tries to 'include' it
    app.connect("builder-inited", run_toml_generator)
