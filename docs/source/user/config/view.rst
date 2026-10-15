.. _config-viewing-docbuild-config-env:

Viewing the Environment Configuration
=====================================

To see the current merged configuration:

.. code-block:: shell

   docbuild config list

Use ``--app`` or ``--env`` to view only the specific configuration.
For details on customizing output styling and colors, see :ref:`config-theme`.


.. _config-viewing-flat:

Showing the Flat Format
-----------------------

By default, :command:`docbuild config list` prints JSON.
Pass the ``--flat`` flag to print one setting per line, with its full dotted key:

.. code-block:: console

   docbuild config list --flat --env

Each line has the form ``<dotted.key> = <value>``.

The flat format is useful for searching for a key with :command:`grep` or comparing two configurations with :command:`diff`. For example, to search for "tmp":

.. code-block:: console

   $ docbuild config list --env --flat | grep tmp
   env.paths.tmp_repo_dir = '/home/tux/.local/state/docbuild/repos/branches'
   env.paths.tmp.tmp_base_dir = '/tmp/docbuild'
   env.paths.tmp.tmp_dir = '/tmp/docbuild/default-env'
   env.paths.tmp.tmp_deliverable_dir = '/tmp/docbuild/default-env/deliverable'
   env.paths.tmp.tmp_metadata_dir = '/tmp/docbuild/default-env/metadata'
   env.paths.tmp.tmp_build_base_dir = '/tmp/docbuild/default-env/build'
   env.paths.tmp.tmp_build_dir_dyn = '{product}-{docset}-{lang}'
   env.paths.tmp.tmp_out_dir = '/tmp/docbuild/default-env/out'
   env.paths.tmp.log_dir = '/home/tux/.local/state/docbuild/default-env/log'
   env.paths.tmp.tmp_deliverable_name_dyn = '{product}_{docset}_{lang}_XXXXXX'


Combine ``--flat`` with ``--app`` or ``--env`` to limit the output to one configuration type.


.. _config-viewing-validate:

Validating Before Listing
-------------------------

By default, :command:`docbuild config list` does not validate the configuration.
If a file is invalid, the command still lists the raw values from the file, and logs a warning.

Pass the ``--validate`` flag to validate the configuration before listing it:

.. code-block:: shell

   docbuild config list --validate

With ``--validate``, docbuild reports any validation error and stops without listing the configuration.
Use this flag to check a new or edited configuration file before you rely on it.
To check a file without listing it, use :command:`docbuild config validate` instead (see :ref:`validate-config`).


.. _config-viewing-unresolved-placeholders:

Viewing Unresolved Placeholders
-------------------------------

By default, :command:`docbuild config list` displays the configuration with all placeholders resolved. To display placeholders without resolving them (useful for debugging), pass the ``-U`` or ``--unresolved`` option:

.. code-block:: shell

   docbuild config list -U

You can combine ``-U`` / ``--unresolved`` with other flags such as ``--flat``, ``--app``, or ``--env``:

.. code-block:: shell

   docbuild config list -U --flat
   docbuild config list -U --env


Debugging Placeholders
----------------------

To inspect the configuration with placeholders left unresolved, use the ``-U`` or ``--unresolved`` flag with :command:`docbuild config list`. See :ref:`config-viewing-unresolved-placeholders`.