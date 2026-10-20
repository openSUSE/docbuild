.. _shell-completion:

Enabling Shell Completion
=========================

The :command:`docbuild` command can complete subcommands, options, and
doctypes when you press :kbd:`Tab`. Completion is not active by default;
enable it once for your shell.


Activating Completion
---------------------

Add the following line to the configuration file of your shell and start a
new shell afterwards.

.. tab-set::

   .. tab-item:: Bash

      Add to :file:`~/.bashrc`:

      .. code-block:: bash

         eval -- "$(_DOCBUILD_COMPLETE=bash_source docbuild)"

   .. tab-item:: Zsh

      Add to :file:`~/.zshrc`:

      .. code-block:: zsh

         # Ensure compinit is loaded (standard in zsh configurations)
         autoload -U compinit && compinit

         eval "$(_DOCBUILD_COMPLETE=zsh_source docbuild)"

   .. tab-item:: Fish

      Create the file :file:`~/.config/fish/completions/docbuild.fish`
      with this content:

      .. code-block:: fish

         _DOCBUILD_COMPLETE=fish_source docbuild | source

The commands above generate the completion script each time a shell starts.
To make startup faster, you can save the script to a file once and source
that file instead, for example for Bash:

.. code-block:: shell-session

   $ _DOCBUILD_COMPLETE=bash_source docbuild > ~/.docbuild-complete.bash

Then add ``. ~/.docbuild-complete.bash`` to your :file:`~/.bashrc`.
Regenerate the file after upgrading :command:`docbuild`.


Completing Subcommands and Options
----------------------------------

Press :kbd:`Tab` after a partial subcommand or option to complete it:

.. code-block:: shell-session

   $ docbuild po<Tab>
   $ docbuild portal

   $ docbuild build --skip-<Tab>
   --skip-metadata     --skip-repo-update


Completing Doctypes
-------------------

Commands that accept doctypes (see :ref:`concept-doctype-syntax`), such as
:command:`docbuild build`, :command:`docbuild portal list`,
:command:`docbuild metadata run`, :command:`docbuild check files`, and the
:command:`docbuild cache` subcommands, complete each
part of the doctype ``PRODUCT/DOCSETS/LANGS`` separately:

Product
   The known product acronyms, for example ``sles`` or ``sle-micro``.

Docset
   The docsets of the product as defined in the portal config of your
   environment, plus the wildcard ``*``.

Language
   All supported language codes, plus the wildcard ``*``.

Type the separator ``/`` before pressing :kbd:`Tab` to complete the next
part. Docsets and languages can be given as a comma-separated list; only the
last item is completed.

.. code-block:: shell-session
   :caption: Completing a doctype step by step

   $ docbuild build sl<Tab>
   sle-ha  sle-hpc  sle-micro  sled  sles  sles-sap  ...

   $ docbuild build sles/<Tab>
   sles/*  sles/15-SP7  sles/16.0

   $ docbuild build sles/16.0/de<Tab>
   $ docbuild build sles/16.0/de-de

Docset completion reads the environment config in the same way as a normal
:command:`docbuild` run, including the ``--env-config`` and
``--set-env`` options given on the command line. If the environment
config or the portal config cannot be loaded, only the wildcard ``*`` is
offered.
