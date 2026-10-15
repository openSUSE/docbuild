.. _cmd_llms:

Creating Markdown for AI Tools
==============================

AI assistants and LLM crawlers often read web pages poorly.
Pages full of navigation menus, scripts, and layout markup waste their limited context on noise.
``docbuild llms`` gives them a cleaner version of your documentation.

Why build Markdown files?
-------------------------

The command converts each built HTML page into a plain Markdown file that keeps only the content.
It also writes an :file:`llms.txt` file, which is an index that points AI tools to all of these Markdown files.
Each HTML page gets a ``<link rel="alternate" type="text/markdown">`` tag, so tools that read the HTML can find the Markdown version.

Use this command when you want AI tools to answer questions about your documentation accurately.
Readers and human visitors still see the normal HTML site.

Requirements
------------

Before you run the command, make sure you have the following:

* A working ``docbuild`` installation.
  See :doc:`install` for details.
* A completed documentation build in the target directory.
  The command reads the existing HTML output and does not rebuild the documentation.
* The following settings, which you can provide either in an ENV config file or with ``-C``:

  * ``paths.target.target_base_dir``: The directory that contains your built deliverables.
  * ``build.build_llmstxt``: Must be ``true`` to enable generation.
    The command exits without doing anything when this option is ``false``.
  * ``paths.llmstxt_dir``: The subdirectory for the Markdown files and the index.
    The default is :file:`docs`.
    A relative path is resolved against ``target_base_dir``.

Running the command
-------------------

To generate the Markdown files for an existing build, do the following:

#. Provide the settings in the way you prefer:

   * In an arbitrary file (like :file:`env.toml`), set the options listed in the section above. docbuild does not search for this name by default, so pass it with ``--env-config env.toml`` and run:

     .. code-block:: console
        :caption: Pass a custom ENV config file

        docbuild --env-config env.toml llms

   * In :file:`env.{role}.toml`, where ``{role}`` is the environment role such as ``devel`` or ``production``, set the options listed in the section above. Store the file in a standard location.
     Run :command:`docbuild llms` from the directory that contains the file. The default role is ``production``, so the default file name is :file:`env.production.toml`.

   * On the command line, pass each setting with ``-C``/ ``--set-env`` as a ``KEY=VALUE`` pair.
     You do not need an ENV config file for this.
     If you also have an env config file, the ``-C`` values override it for that run.

     .. code-block:: console
        :caption: Pass the settings on the command line

        docbuild -C paths.target.target_base_dir=/path/to/builds \
                 -C build.build_llmstxt=true \
                 llms

#. Check the output directory.
   It contains the Markdown files and :file:`llms.txt` in the ``llmstxt_dir`` subdirectory.

.. note::

   Run the command again after each new build to update the Markdown files.
   If you enable ``build.build_llmstxt`` for your normal builds, the Markdown files are generated during the build and you do not need this command.
