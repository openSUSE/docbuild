.. _config-tomlfile:
.. _config-concepts:

Understanding Docbuild Configuration
====================================

.. note::

   To prevent accidental commits of sensitive information, all configuration files matching the :file:`env.*.toml` pattern in the root directory are ignored by Git.
   However, this rule does not apply to files within the :file:`etc/` directory.



.. _config-defaults:

Built-in Defaults
-----------------

Docbuild ships with built-in, hard-coded default values for both application and environment configurations.
These defaults form the base layer for all operations.

No configuration file is required if the defaults meet your needs.
When configuration files exist, their values merge on top of the built-in defaults.



.. _config-merging:

How Multiple Files Combine
--------------------------

Docbuild does not pick a single file from the search directories.
It loads every matching file and deep-merges them on top of the built-in defaults, in precedence order.
Keys that a file does not set keep the value from a lower-priority source.


.. _config-standard-vs-custom:

Standard and Custom Configuration Modes
---------------------------------------

Docbuild works in one of two modes for each configuration type:

Standard search (default)
  Docbuild searches the system, user, and project directories, as described above.

Explicit file (custom)
  Docbuild skips the search for that configuration type and loads only the file you pass with ``--app-config`` or ``--env-config``.
  The file still merges on top of the built-in defaults.
  Files in the system, user, and project directories are ignored for that type.

Command-line overwrites (``-C`` and ``--set-env``) apply on top of either mode.


.. _config-env-role:

Environment Roles
-----------------

Docbuild recognizes these role values:

* ``production``, ``prod``, or ``p``.
* ``staging``, ``stage``, or ``s``.
* ``testing``, ``t``, ``test``, ``dev``, or ``devel``.

A role identifies which environment a configuration file applies to.
To work with roles in practice, see :ref:`config-use-multiple-env-configs`.
