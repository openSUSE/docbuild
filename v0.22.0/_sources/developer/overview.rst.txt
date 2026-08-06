Overview
========

The project's repository is structured in a way that allows for easy navigation and understanding of its components. Here are some key concepts to help you get started:

* **Source Structure**

  The source code uses the ``src/`` directory layout, which is a common practice in Python projects. This structure helps to avoid issues with module imports and makes it clear which files are part of the package.

* **Test Suite**

  The test suite is located in the ``tests/`` directory. It contains unit tests to ensure the quality and functionality of the code. The tests are organized in a way that mirrors the source structure, making it easier to find and run tests related to specific modules.

* **pyproject.toml**

  The :file:`pyproject.toml` file is used to define the project's metadata, dependencies, and build system requirements. It is a standardized way to configure Python projects and is used by tools such as :command:`uv` (see `uv docs <https://docs.astral.sh/uv/>`_).
  The :command:`uv` create a lock file :file:`uv.lock` based on the dependencies defined in :file:`pyproject.toml`. This lock file ensures that the same versions of dependencies are used across different environments, providing consistency and reliability.

* **uv**

  The project uses :command:`uv` as the primary command-line interface for managing the development environment, running tests, and building documentation. It provides a consistent way to interact with the project and its components.
  Its configuration is defined in the :file:`uv.toml` file.

* **Documentation**

  The documentation is built using `reStructuredText <https://docutils.sourceforge.io/rst.html>`_ and `Sphinx <https://www.sphinx-doc.org/en/master/>`_. The source files for the documentation are located in the :file:`docs/` directory. The documentation targets users and developers, providing information on how to use the project, its features, and how to change it.