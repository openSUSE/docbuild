.. _cmd_llms:

docbuild llms
=============

Synopsis
--------

.. code-block:: bash

   docbuild llms [OPTIONS]

Description
-----------

To expose your documentation to AI systems and LLM crawlers, this command generates lightweight Markdown equivalents and an :file:`llms.txt` index from your pre-built HTML output. This command directly scans the existing directory, cleans the HTML, converts it to Markdown, and injects the necessary ``<link rel="alternate">`` tags.

Configuration
-------------

The command automatically relies on the following settings in your environment configuration (:file:`env.toml`):

* ``paths.target.target_base_dir``: The directory containing built deliverables to be processed.
* ``build.build_llmstxt``: Boolean flag enabling or disabling LLMs generation.
* ``paths.llmstxt_dir``: The subdirectory name where the generated Markdown files will be stored (defaults to :file:`docs`). If given as a relative path, it resolves relative to ``target_base_dir``.

To temporarily override any configuration setting use the ``-C`` option:

.. code-block:: bash

   docbuild -C paths.target.target_base_dir=/path/to/builds -C build.build_llmstxt=true llms
