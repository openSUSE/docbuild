.. _setting-devel-environment:

Setting Development Environment
===============================

This document provides instructions for setting up a development environment for this project.

.. admonition:: Note: A Quick Word on Virtual Environments
   :name: note-uv-venv

   The |uv| tool can work with or without activating a Python virtual environment (venv). When |uv| finds a :file:`.venv` directory, it
   uses it automatically. There is no need to "activate" it.
   However, if you get used to activating your Python VENV's, it's
   possible to do so.


The following steps are recommended to set up your development environment:

1. Follow the steps in :ref:`prepare-installation` and :ref:`installing-docbuild`.

2. If you haven't created a virtual environment, do so:

   .. code-block:: shell-session

      $ uv venv --prompt venv313 --python 3.13 .venv

   Keep in mind that the Python version used in the virtual environment should match the version specified in the :file:`pyproject.toml` file.
   
   The example above uses Python 3.13, but you can adjust it according to your needs as long as it is compatible with the project.
   See file :file:`pyproject.toml` in ``project.requires-python`` for the exact version.

3. Syncronize the virtual environment with the project dependencies, but use the development group instead of the default group:

   .. code-block:: shell-session

      $ uv sync --group devel

4. Optionally, source the shell aliases defined in :file:`devel/activate-aliases.sh` to abbreviate the longer :command:`uv` calls.

   .. code-block:: shell-session

      $ source devel/activate-aliases.sh

   This helps to shorten the command names, making it easier to work with the project. For example, you can use :command:`upytest` instead of typing :command:`uv run pytest` for running the test suite.

After completing these steps, you will have a virtual environment set up with the necessary dependencies for development.