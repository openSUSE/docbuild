.. _config-init:

Creating Starter Configuration
==============================

Run the following command to create application and environment configuration
files from Docbuild's built-in defaults:

.. code-block:: shell-session

   $ docbuild config init

The command creates :file:`config.toml` and :file:`env.production.toml` in the user
configuration directory and prints their paths. This is the same directory
Docbuild searches when loading configuration: typically
:file:`~/.config/docbuild` on Linux (or :file:`$XDG_CONFIG_HOME/docbuild` when set),
and :file:`~/Library/Application Support/docbuild` on macOS.
Missing directories are created automatically.

To create only one file, use ``--app`` or ``--env``:

.. code-block:: shell-session

   $ docbuild config init --app
   $ docbuild config init --env

Passing both flags is equivalent to passing neither. To preview the paths
without creating directories or files, use the global ``--dry-run`` option:

.. code-block:: shell-session

   $ docbuild --dry-run config init

Existing files, directories and symbolic links are never overwritten. If any
selected destination already exists, the command fails before writing files.
Use the flag for the missing configuration, or back up and move an existing
file yourself before trying again.

:command:`config init` does not load existing configuration. Global configuration
selection options and ``--set-env`` overrides do not change the generated
defaults or their destination. The generated files preserve placeholders,
such as ``{root_config_dir}`` and ``{{dcfile}}``, for resolution when Docbuild
loads them or runs a build. Optional values that are unset are omitted because
TOML has no null value.

The files include a generated-file header; comments from the example templates
are not copied. Edit the generated environment configuration for your portal,
then check it with :ref:`validate-config`.

Choosing an Environment Role
----------------------------

Use ``--role`` to create an environment configuration for production (the
default), staging or testing:

.. code-block:: shell-session

   $ docbuild config init --env --role staging

This creates :file:`env.staging.toml` with ``general.role`` set to ``staging``.
Without ``--env``, the command also creates :file:`config.toml`. Role aliases
are case-insensitive: ``Prod`` selects production and ``dev`` selects testing.
An explicit ``--role`` cannot be combined with ``--app``.
