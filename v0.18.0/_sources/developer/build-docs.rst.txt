.. _build-docs:

Building Documentation
======================

To build the documentation for this project, use the following steps:

#. Prepare your environment by following the instructions in :ref:`prepare-devel-env`.

#. Build the HTML documentation using the :ref:`makedocs <devel-helpers>` command:

   .. code-block:: shell-session
      :name: makedocs

      makedocs

   If you want to have a bit more control, use this command:

   .. code-block:: shell-session
      :name: sphinx-build

      uv run --frozen make -C docs html

#. Watch for warnings and errors during the build process.
   If you encounter any issues, review the output and fix them accordingly.

Find the generated documentation in the :file:`docs/build/html` directory.
