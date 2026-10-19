.. _cmd_llms:

Creating Markdown for AI Tools
==============================

AI assistants and LLM crawlers often read web pages poorly.
Pages full of navigation menus, scripts, and layout markup waste their limited context on noise.
:command:`docbuild llms` gives them a cleaner version of your documentation.

Why build Markdown files?
-------------------------

The command converts each built HTML page into a plain Markdown file with YAML frontmatter that keeps only the content and key metadata.
It also writes an :file:`llms.txt` index in each deliverable's target HTML directory that points AI tools to all of these Markdown files.
Each HTML page receives ``<link rel="alternate" type="text/markdown">`` tags in its ``<head>`` pointing to its Markdown counterpart and to :file:`llms.txt`, so tools that inspect the HTML can discover the Markdown version automatically.

Use this command when you want AI tools to answer questions about your documentation accurately.
Readers and human visitors still see the normal HTML site.

Requirements
------------

Before you run the command, make sure you have the following:

* A working :command:`docbuild` installation.
  See :doc:`install` for details.
* A completed documentation build in the target directory (for standard :term:`DAPS` deliverables) or prebuilt HTML files in the prebuilt directory (for :term:`pre-built deliverables <Pre-built Deliverable>`).
  The command reads existing HTML output and does not run DAPS to rebuild documentation from source.
* The following settings, which you can provide either in an :ref:`ENV config file <ref-env-toml>` or on the command line with ``-C`` / ``--set-env``:

  * ``paths.main_portal_config``: Path to the main :term:`Portal Config` XML file used to resolve :term:`doctypes <Doctype>` and deliverables.
  * ``paths.target.target_base_dir``: The root directory that contains your built deliverables and receives the generated Markdown and :file:`llms.txt` files.
  * ``paths.prebuilt_dir``: The directory that contains prebuilt HTML deliverables (for example, Antora builds).
    When processing a prebuilt deliverable, :command:`docbuild llms` copies its HTML files from ``paths.prebuilt_dir`` into the target HTML directory under ``paths.target.target_base_dir`` before generating the Markdown files.
  * ``build.build_llmstxt``: Must be ``true`` to enable generation.
    The command exits without doing anything when this option is ``false``.
  * ``paths.llmstxt_dir``: The subdirectory inside each deliverable's target HTML directory where the converted Markdown files are stored.
    The default is :file:`docs`.

Running the command
-------------------

.. code-block:: console
   :caption: Synopsis of :command:`docbuild llms`

   docbuild llms [--all] [DOCTYPES]...

Specify either one or more :term:`doctypes <Doctype>` (such as ``sles/16.0/en-us`` or ``cloudnative/rancher-ai/en-us``) or ``--all`` to process all configured deliverables.
The ``--all`` option and doctype arguments are mutually exclusive.

To generate the Markdown files for existing deliverables, do the following:

#. Provide the required configuration settings and run :command:`docbuild llms`:

   * To use an arbitrary configuration file (such as :file:`env.toml`), pass it with ``--env-config``:

     .. code-block:: console
        :caption: Run for all deliverables with a custom ENV config file

        docbuild --env-config env.toml llms --all

   * To use an environment role file (:file:`env.{role}.toml`, such as :file:`env.production.toml` or :file:`env.devel.toml`), store it in a standard configuration directory or the current working directory and run:

     .. code-block:: console
        :caption: Run for a specific doctype using the default environment config

        docbuild llms sles/16.0/en-us

   * To override or supply settings directly on the command line without editing a configuration file, pass each setting with ``-C`` / ``--set-env`` as a ``KEY=VALUE`` pair:

     .. code-block:: console
        :caption: Pass settings on the command line for a prebuilt doctype

        docbuild -C paths.target.target_base_dir=/path/to/builds \
                 -C paths.prebuilt_dir=/path/to/prebuilt \
                 -C build.build_llmstxt=true \
                 llms cloudnative/rancher-ai/en-us

#. Verify the generated files in the deliverable's target HTML directory (for example, :file:`/path/to/builds/en-us/cloudnative/rancher-ai/html/`):

   * :file:`llms.txt` is written at the root of the deliverable's ``html`` directory.
   * Converted Markdown files (``.md``) are written inside the ``paths.llmstxt_dir`` subdirectory (by default :file:`docs/`).

.. note::

   Run the command again after each new build to update the Markdown files.
   If you enable ``build.build_llmstxt = true`` for your normal :command:`docbuild build` runs, the Markdown and :file:`llms.txt` files are generated automatically during the build and you do not need to run :command:`docbuild llms` separately.
