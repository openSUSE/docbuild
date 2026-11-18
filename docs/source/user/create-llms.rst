.. _cmd_llms:

Creating Markdown for AI Tools
==============================

AI assistants and LLM crawlers often read web pages poorly.
Pages full of navigation menus, scripts, and layout markup waste their limited context on noise.
:command:`docbuild build llms` gives them a cleaner version of your documentation.

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

Excluding files from LLM output
-------------------------------

Some files, like the GPL license page, add unnecessary noise for AI tools. You can exclude files from the Markdown generation using the ``[llms]`` section in your ENV config.

* ``[llms].exclude``: An array of filenames or shell glob patterns (``*``, ``?``) to ignore. The default includes :file:`doc-gfdl-license.html`.
* ``[llms].exclude-extra``: An array of additional files to ignore. 

If you want to ignore new files for your specific project, it is recommended to add them to ``[llms].exclude-extra`` rather than overwriting the default ``exclude`` list.

|project| merges ``exclude`` and ``exclude_extra`` into a single list, placing  ``exclude`` items first followed by ``exclude_extra``. Any duplicate patterns are removed while preserving their original order.

Running the command
-------------------

To generate the Markdown files for an existing build, you can run the command against your entire target directory, or you can pass specific doctypes (like ``sles/15-SP6/en-us``) to only process specific products. 
(Use the ``--all`` flag to process the entire directory).

Do the following:

#. Provide the settings in the way you prefer:

   * In an arbitrary file (like :file:`env.toml`), set the options listed in the section above. docbuild does not search for this name by default, so pass it with ``--env-config env.toml`` and run:

     .. code-block:: console
        :caption: Pass a custom ENV config file

        $ docbuild --env-config env.toml build llms

   * In :file:`env.{role}.toml`, where ``{role}`` is the environment role such as ``devel`` or ``production``, set the options listed in the section above. Store the file in a standard location.
     Run :command:`docbuild build llms` from the directory that contains the file. The default role is ``production``, so the default file name is :file:`env.production.toml`.

   * On the command line, pass each setting with ``-C``/ ``--set-env`` as a ``KEY=VALUE`` pair.
     You do not need an ENV config file for this.
     If you also have an env config file, the ``-C`` values override it for that run.

     .. code-block:: console
        :caption: Pass the settings on the command line

        $ docbuild -C paths.target.target_base_dir=/path/to/builds \
             -C build.build_llmstxt=true \
             build llms

#. Check the output directory.
   It contains the Markdown files and :file:`llms.txt` in the ``llmstxt_dir`` subdirectory.

.. note::

   Run the command again after each new build to update the Markdown files.
   If you enable ``build.build_llmstxt`` for your normal builds, the Markdown files are generated during the build and you do not need this command.
