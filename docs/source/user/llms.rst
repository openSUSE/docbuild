.. _cmd_llms:

docbuild llms
=============

Synopsis
--------

.. code-block:: bash

   docbuild llms [OPTIONS]

Description
-----------

This command is useful when you already have an existing HTML build directory but are missing the associated Markdown files and :file:`llms.txt` index. Instead of running a full, time-consuming DAPS or Antora build process, this command directly scans the existing directory, cleans the HTML, converts it to Markdown, and injects the necessary ``<link rel="alternate">`` tags.

Configuration
-------------

The command automatically relies on the following settings in your environment configuration (:file:`env.toml`):

* ``paths.target.target_base_dir``: The directory containing built deliverables to be processed.
* ``build.build_llmstxt``: Boolean flag enabling or disabling LLMs generation.
* ``paths.llmstxt_dir``: The subdirectory name where the generated Markdown files will be stored (defaults to :file:`docs`).

You can temporarily override any configuration setting using the ``-C`` option:

.. code-block:: bash

   docbuild -C paths.target.target_base_dir=/path/to/builds -C build.build_llmstxt=true llms

