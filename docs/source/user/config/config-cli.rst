.. _config-overwriting-cli:

Overwriting Config Options on the Command Line
==============================================

To temporarily override environment configuration options directly from the command line use the ``-C`` or ``--set-env`` option. This avoids having to create or modify TOML files for quick adjustments.

Use ``key=value`` syntax, and use dot notation for nested options:

.. code-block:: shell-session

     $ docbuild -C "general.canonical_url_domain=https://doc.example.net" -C paths.root_config_dir=/etc/docbuild config list --env

Options passed via ``-C`` or ``--set-env`` have the highest priority and will strictly overwrite the corresponding settings loaded from your default, system, or local configuration files.

.. important::

   Values passed via ``-C`` or ``--set-env`` are subject to the same validation rules as configuration files. If a value does not comply with the :term:`Pydantic` model (for example, an invalid enum value or incorrect data type), the command will fail with a clear validation error describing what is required.


Handling Keys with Dots
-----------------------

If your configuration keys contain dots, use quotes or brackets to prevent them from being treated as nested separators:

* **Single quotes** (Syntax ``'key.with.dots'``)

  .. code-block:: shell-session

     $ docbuild -C "xslt.html.'show.edit.link'=1" config list --env

* **Double quotes** (Syntax ``"key.with.dots"``)

  .. code-block:: shell-session

     $ docbuild -C 'xslt.html."show.edit.link"=1' config list --env

* **Square brackets** (Syntax ``[key.with.dots]``)

  .. code-block:: shell-session

     $ docbuild -C "xslt.html.[show.edit.link]=1" config list --env

All three syntaxes are equivalent. Choose whichever is most convenient for your shell environment.


Type Conversion
---------------

Values are automatically converted to their appropriate types:

* **Booleans**: ``true`` and ``false`` (case-insensitive)

  .. code-block:: shell-session

     $ docbuild -C "general.enabled_mail=true" config list --env

* **Strings**: Quoted strings or values that don't match the above patterns

  .. code-block:: shell-session

     $ docbuild -C "general.name='My ENV Name'" config list --env



Using placeholders in CLI overrides
-----------------------------------

It is possible to use placeholders in CLI overrides, just like in configuration files. Static placeholders will be resolved based on the current configuration context, while dynamic placeholders will remain as templates for runtime resolution:

.. code-block:: shell-session

   $ docbuild -C 'general.canonical_url_domain=https://docs.example.org' \
              -C 'xslt.html.homepage={general.canonical_url_domain}' \
              config list --env | grep example
   "canonical_url_domain": "https://docs.example.org/"
      "homepage": "https://docs.example.org"


Validation of CLI Values
------------------------

CLI overrides are validated against the same rules as configuration files. However, validation timing depends on the subcommand:

* **Validation occurs** when running actual commands (e.g., ``docbuild build``, ``docbuild repo clone``)
* **Validation is skipped** by default with ``docbuild config list`` for convenience (to view raw config even if invalid)

To validate CLI overrides before running a command, use one of these options:

* Run the command that uses the config (validation happens automatically)
* Use ``docbuild config validate`` to check the config without running a full command
* Use ``docbuild config list --validate`` to force validation when listing config


Example: Invalid Enum Value
---------------------------

If you pass an invalid value via ``-C`` or ``--set-env``, the command will fail with a clear validation error:

.. code-block:: shell-session

      $ docbuild -C "general.role=invalid_role" build
      1 Validation error in config file 'unknown':

      (1) In 'general.role':
         Input should be 'production', 'staging', 'testing' or other valid values
         Expected: Environment Role
         See: https://opensuse.github.io/docbuild/latest/errors/enum.html

To find the valid values for a field, check the error message or consult the configuration reference documentation. You can also validate the config explicitly with ``docbuild config validate``:

.. code-block:: shell-session

      $ docbuild -C "general.role=invalid_role" config validate
      1 Validation error in config file 'unknown':
      (1) In 'general.role': Input should be 'production', 'staging', 'testing' ...

      $ docbuild -C "general.role=production" config validate
      ✓ Configuration is valid
