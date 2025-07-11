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

The code is developed on openSUSE, but should work on any Linux distribution.
The project will support MacOS too. It's currently not planned to support Windows.


.. note::

    If you use a different OS than Linux, dependency resolution may be challenging. Either the required package is not available for your OS or it is hard to get it right.

    You may have a better experience developing in a virtual machine running openSUSE or using a Docker container.


Python
------

The minimal Python version is defined in the :file:`pyproject.toml` file. It's strongly recommended to have the Python versions managed by |uv|.


Editor
------

You can use any editor you like. Rudimentary support is available for `VSCode <https://code.visualstudio.com/>`_.


External tools
--------------

* |daps|: our tool to build documentation. This is an obligatory requirement. This adds other dependencies.
* |uv|, the Python package manager. This is explained in :ref:`devel-helpers`.
* :command:`make` is used to build the documentation.
* :command:`jing`: for validation the XML configuration files.
* :command:`gh`: optional tool for interacting with GitHub, see :ref:`github-cli`.



XML configuration
-----------------

Formerly known as the *Docserv XML configs*. These configuration files defines the :term:`products <Product>`, their :term:`releases <Docset>`, their :term:`lifecycle <Lifecycle>` status and more.

Clone the |gl_xmlconfig| or use the RNC schema from :gh_tree:`src/docbuild/config/xml/data/` to create this configuration.
