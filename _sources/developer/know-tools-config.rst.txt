.. _know-tools-config:

Knowning the Tools Config Files
===============================

This project uses several configuration files to manage its settings. While it
is possible to consolidate many tool settings into the :file:`pyproject.toml`
file, this project intentionally keeps most configurations in separate,
dedicated files. This approach promotes clarity and modularity, making it
easier to understand and manage the settings for each specific tool.

* :file:`.gitignore`
  This file tells Git which files and directories to ignore.

* :file:`pyproject.toml`
  This is the central configuration file for the project, based on :pep:`621`. It
  primarily defines project metadata (like name, version, and dependencies) and
  build system requirements for the ``setuptools`` build backend.

* :file:`.pytest.ini`
  This file contains configuration for the :term:`Pytest` testing framework. It
  specifies options such as test paths, Python path for imports, and default
  command-line arguments for running tests, including coverage analysis and
  doctest settings.

* :file:`.ruff.toml`
  This file configures the Ruff linter and formatter. It defines the
  target Python version, line length, which linting rules to enable or
  disable, and any per-file rule overrides.

* :file:`towncrier.toml`
  This file configures Towncrier, the tool used to generate the project's
  :term:`Changelog`. It specifies the location of news fragments, the
  changelog file itself, and the different types of changes.

* :file:`uv.toml`
  This file provides project-specific configuration for the |uv| package
  manager.

* :file:`.vscode/`
  This directory contains workspace-specific settings for Visual Studio Code.
  It can include recommended extensions (:file:`extensions.json`), debug
  configurations (:file:`launch.json`), and shared workspace settings
  (:file:`settings.json`) to ensure a consistent development experience for
  all contributors using this editor.