.. _update-package:

Updating a Specific Package
===========================

If you want to update a specific package in your project, but at the same
time keep the development group dependencies intact, use the following command:

.. code-block:: shell-session

   uv sync --group devel --upgrade-package pydantic-core

