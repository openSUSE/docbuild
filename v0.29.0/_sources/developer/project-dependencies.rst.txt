.. _project-deps:

Project Dependencies
====================

Although this project contains pure Python code, it needs other dependencies to work correctly:

* **Python installation dependencies**

  Minimum dependencies that the program can run at all.

* **Testing dependencies**

  Dependencies used for testing.

* **Documentation Dependencies**

  For building the documentation.

* **System dependencies**

  These are explained in this topic.

All of the above points (except for the last one) are defined in the :file:`pyproject.toml` file.


Operating System
----------------

The code is developed on `openSUSE <https://www.opensuse.org/>`_, but should work on any Linux distribution.
The project will support MacOS too. It's currently not planned to support Windows.


.. note::

    If you use a different OS than Linux, dependency resolution may be challenging. Either the required package is not available for your OS or it is hard to get it right.

    You may have a better experience developing in a virtual machine running openSUSE or using a Docker container.


Python
------

The minimal Python version is defined in the :file:`pyproject.toml` file. It is strongly recommended to have the Python versions managed by |uv|.


Editor
------

You can use any editor you like. Rudimentary support is available for `VSCode <https://code.visualstudio.com/>`_.


External tools
--------------

* |daps|: Our tool to build documentation. This is an obligatory requirement. This adds other dependencies.
* |uv|: The Python package and project manager. This is explained in :ref:`devel-helpers`.
* :command:`make`: Used to orchestrate the documentation build process.
* `jing <https://jing.nu/>`_: For validating the XML configuration files against their RNC schema.
* `gh <https://cli.github.com/>`_: The GitHub CLI, an optional tool for GitHub interactions. See :ref:`github-cli`.
