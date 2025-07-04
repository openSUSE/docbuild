"""Configuration file for the Sphinx documentation builder."""
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

from docbuild.__about__ import __version__

project = 'docbuild'
copyright = '2025, Tom Schraitle'  # noqa: A001
author = 'Tom Schraitle'
release = __version__

gh_user = 'openSUSE'
gh_repo_url = f'https://github.com/{gh_user}/{project}'
gh_repo_slug = f'{gh_user}/{project}'


# --- Prolog configuration
rst_prolog = f"""
.. |project| replace:: {project}
.. |gh_repo_slug| replace:: {gh_repo_slug}
.. |github_user| replace:: {gh_user}
.. |gh_repo| replace:: {gh_repo_url}
.. |gh_repo_url| replace:: `{gh_repo_slug} <{gh_repo_url}>`__
.. |uv| replace:: :command:`uv`
.. |gh_release| replace:: `Releases <{gh_repo_url}/releases/>`__
"""

# -- General configuration
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinx.ext.doctest',
    'sphinx.ext.extlinks',
    # For documenting click CLI commands:
    'sphinx_click',
    # Copy button in code blocks:
    'sphinx_copybutton',
    # For automatic API documentation generation:
    'sphinx_autodoc_typehints',
    # For generating API documentation from docstrings:
    'autoapi.extension',
]

templates_path = ['_templates']
exclude_patterns = []

language = 'en'

# -- Options for autoapi extension
# https://sphinx-autoapi.readthedocs.io/en/latest/reference/config.html
autoapi_modules = {
    'docbuild': None,
    # {
    #     # "output": "reference/_autoapi",
    #     # "prune": True|False,
    #     # "override": True|False,
    #     # "template":
    # }
}
autoapi_root = 'reference/_autoapi'
autoapi_dirs = ['../../src/']
autoapi_type = 'python'
autoapi_add_toctree_entry = False
# autoapi_template_dir = "_templates/autoapi"
autoapi_options = [
    'members',
    # "undoc-members",
    'inherited-members',
    'show-inheritance',
    'show-module-summary',
    'imported-members',
    'special-members',
    'show-inheritance-diagram',  # needs sphinx.ext.inheritance_diagram & graphviz
    # "private-members",
]
autoapi_keep_files = True
autodoc_typehints = 'signature'
autoapi_own_page_level = 'class'


# -- Options for extlinks extension ------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/extlinks.html
extlinks = {
    # Example for linking to a specific file/path in the repo:
    'gh_path': (f'{gh_repo_url}/blob/main/%s', '%s'),
    # Linking to the GH issue tracker:
    'issue': (f'{gh_repo_url}/issues/%s', 'issue #%s'),
}


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output


autosummary_generate = False
autodoc_default_options = {
    'members': True,
    'undoc-members': False,
    'show-inheritance': True,
    'inherited-members': False,
    'private-members': True,
}

html_theme = 'pydata_sphinx_theme'
# html_theme = "alabaster"

html_static_path = ['_static']

html_css_files = [
    'css/custom.css',
]

html_context = {
    'github_user': gh_user,
    'github_repo': project,
    'github_version': 'main',
    'doc_path': 'docs/source/',
}

html_theme_options = {
    'announcement': 'Documentation is under construction.',
    'show_prev_next': True,
    # "html_last_updated_fmt": "%b %d, %Y",
    'content_footer_items': ['last-updated'],
    'github_url': gh_repo_url,
    #   "external_links": [
    #       {"name": "link-one-name", "url": "https://<link-one>"},
    #   ],
    #
    'icon_links': [
        {
            'name': 'GitLab susedoc/docserv-config',
            'url': 'https://gitlab.suse.de/susedoc/docserv-config',
            'icon': 'fa-brands fa-square-gitlab',
            'type': 'fontawesome',
        },
    ],
    #
    'use_edit_page_button': True,
    'back_to_top_button': True,
    'logo': {
        'text': 'Docbuild Documentation',
        # "image_light": "_static/logo-light.png",
        # "image_dark": "_static/logo-dark.png",
    },
}

html_logo = '_static/logo.png'

# -- Options for intersphinx extension ---------------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html#configuration

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'pydantic': ('https://docs.pydantic.dev/latest/', None),
    'click': ('https://click.palletsprojects.com/en/latest/', None),
    'jinja2': ('https://jinja.palletsprojects.com/en/latest/', None),
}
