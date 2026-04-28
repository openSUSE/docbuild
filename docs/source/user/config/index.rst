Viewing and Validating Configuration
------------------------------------

You can Use the :command:`config` subcommand to list or validate your current settings.

Listing Configuration
~~~~~~~~~~~~~~~~~~~~~

To see the current merged configuration:

.. code-block:: shell

   docbuild config list

Use the ``--flat`` flag to see the dotted-path format, or filter by ``--app`` or ``--env``.

Validating Configuration
~~~~~~~~~~~~~~~~~~~~~~~~

To ensure your TOML files match the required schema:

.. code-block:: shell

   docbuild config validate

This checks both application and environment files. You can also validate them individually using the ``--app`` or ``--env`` flags.
