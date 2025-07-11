.. _prepare-devel-env:

Preparing Your Development Environment
======================================

This document provides instructions for setting up a development environment for this project.

.. admonition:: Note: A Quick Word on Virtual Environments
   :name: note-uv-venv

   The |uv| tool can work with or without activating a Python virtual environment (venv). When |uv| finds a :file:`.venv` directory, it
   uses it automatically. There is no need to "activate" it.
   However, if you get used to activating your Python VENV's, it's
   possible to do so.


High-level project overview
---------------------------

The following diagram illustrates the relationship between the main components of the project:

.. graphviz::
   :name: fig-high-level-overview
   :align: center
   :caption: High-level project overview

   digraph "Project Components" {
      rankdir="LR";
      node [shape=box, style="rounded,filled", fillcolor="#E6F2FF"];

      "pyproject" [label="pyproject.toml\nConfiguration"];
      "uv" [label="uv\nPackage Manager"];
      "src" [label="src/\nSource Code"];
      "tests" [label="tests/\nTests"];
      "docs" [label="docs/ and changelog.d/\nDocumentation"];
      "towncrier" [label="towncrier\nChangelog Tool"];

      "pyproject" -> "uv" [label="configures"];
      "uv" -> {"src", "tests", "docs"} [label="manages dependencies for"];
      "towncrier" -> "docs" [label="generates changelog in"];
   }


.. _devel-helpers:

.. include:: devel-helpers.rst
   :start-after: -text-begin-


.. _github-cli:

GitHub CLI
----------

GiHub CLI is a command-line tool named :command:`gh` that allows you to interact with GitHub repositories and perform various tasks directly from the terminal.

It is not required for this project, but it can be useful for managing issues, pull requests, and other GitHub-related tasks directly from the terminal.

Find more information at `GitHub CLI <https://cli.github.com/>`_.


Setting up the development environment
--------------------------------------

The following steps are recommended to set up your development environment:

#. Follow the steps in :ref:`prepare-installation` and :ref:`installing-docbuild`.

#. If you haven't created a virtual environment, do so:

   .. code-block:: shell-session
      :caption: Creating a virtual environment with |uv|
      :name: uv-venv

      $ uv venv --prompt venv313 --python 3.13 .venv

   Keep in mind that the Python version used in the virtual environment should match the version specified in the :file:`pyproject.toml` file.
   
   The example above uses Python 3.13, but you can adjust it according to your needs as long as it is compatible with the project.
   See file :file:`pyproject.toml` in ``project.requires-python`` for the exact version.

#. Synchronize the virtual environment with the project dependencies, but use the development group instead of the default group:

   .. code-block:: shell-session
      :caption: Synchronizing the virtual environment with the development dependencies
      :name: uv-sync-devel

      $ uv sync --frozen --group devel

   The option ``--frozen`` ensures that the dependencies are installed exactly as specified in the lock file, preventing any unexpected changes.

#. Optionally, source the shell aliases defined in :file:`devel/activate-aliases.sh` to abbreviate the longer :command:`uv` calls (see :ref:`devel-helpers` for more information):

   .. code-block:: shell-session
      :caption: Activating the shell aliases for development
      :name: activate-aliases

      $ source devel/activate-aliases.sh


After completing these steps, your development environment is ready to go.


Getting Docserv's Config Files
------------------------------

The ``docbuild`` tool relies on a central set of XML configuration files to
build SUSE product documentation. These files, which define all products,
docsets, and their deliverables, are managed in the ``susedoc/docserv-config``
repository.

To get started, clone this repository to your local machine (you need VPN access):

.. code-block:: shell-session

   $ git clone https://gitlab.suse.de/susedoc/docserv-config.git

You will later need to point ``docbuild`` to the location of this cloned
repository in your configuration.