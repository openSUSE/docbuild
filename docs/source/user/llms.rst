.. _docbuild_llms:

Generating LLM Context Files
============================

The :command:`docbuild llms` subcommand is used to retroactively generate Markdown and ``llms.txt`` files for an existing build directory.

.. code-block:: bash
   :caption: Synopsis of :command:`docbuild llms`

   docbuild llms [OPTIONS]

This command is useful when you already have an existing HTML build directory but are missing the associated Markdown files and ``llms.txt`` index. Instead of running a full, time-consuming DAPS or Antora build process, this command directly scans the existing directory, cleans the HTML, converts it to Markdown, and injects the necessary ``<link rel="alternate">`` tags.

Configuration
-------------
The command automatically relies on the following settings in your environment configuration (``env.toml``):

* ``paths.prebuilt_dir``: The target directory containing the existing HTML files.
* ``build.build_llmstxt``: Must be set to ``true`` (the default). If disabled, the command will exit safely.
* ``paths.llmstxt_dir``: The subdirectory name where the generated Markdown files will be stored (defaults to ``docs``).

If you want to run the command while overriding the configuration temporarily, you can use the ``-C`` option:

.. code-block:: bash

   docbuild -C paths.prebuilt_dir=/tmp/my-builds llms
