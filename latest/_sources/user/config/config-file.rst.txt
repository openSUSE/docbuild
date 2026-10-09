.. _config-tomlfile:


Using a TOML Configuration File
===============================

.. note::

   To prevent accidental commits of sensitive information, all configuration files matching the :file:`env.*.toml` pattern in the root directory are ignored by Git. However, this rule does not apply to files within the :file:`etc/` directory.


.. _config-search-locations:
.. _config-places:

Configuration Search Locations and File Names
---------------------------------------------

Docbuild uses two types of TOML configuration files:

* **Application configuration** (``app``): Controls tool-wide settings such as logging, themes, and concurrency limits.
* **Environment configuration** (``env``): Controls environment-specific settings such as paths, repositories, products, and build targets.

Both configuration types follow the same search hierarchy and precedence order.
The only difference is the file naming.


Built-in Defaults as Foundation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Docbuild ships with built-in, hard-coded default values for both application and environment configurations.
These defaults form the base layer for all operations.

You do not need to create any configuration file if the built-in defaults satisfy your requirements.
When configuration files are present, their values overlay and merge with the built-in defaults.

To inspect the current configuration and its defaults, use the ``config list`` subcommand:

.. code-block:: console

   $ docbuild config list

Use the ``--app`` or ``--env`` flags to inspect a specific configuration type (see :ref:`config-viewing-docbuild-config-env`).


Search and Precedence Order
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Docbuild resolves configuration by evaluating sources in order of increasing priority.
Settings from higher-priority levels overlay and overwrite settings from lower-priority levels:

#. **Built-in defaults:** Hard-coded base values (lowest priority).
#. **System directory:** :file:`/etc/docbuild/`
#. **User directory:** OS-specific user configuration directory resolved via `platformdirs <https://platformdirs.readthedocs.io/>`_.
   On Linux, this adheres to the XDG Base Directory Specification using :envvar:`XDG_CONFIG_HOME` (defaults to :file:`~/.config/docbuild/` when unset).
   On macOS, it defaults to :file:`~/Library/Application Support/docbuild/`.
#. **Project directory:** Current working directory.
#. **Command-line overwrites:** Specified with ``-C`` or ``--set-env`` take precedence over all files (see :ref:`config-overwriting-cli`). This values have the highest priority.


Configuration File Names
~~~~~~~~~~~~~~~~~~~~~~~~

While the search order is identical, application and environment configurations use different file names.

Application configuration
  In each search directory, Docbuild searches for the first existing file from the following list:

  #. :file:`.config.toml`
  #. :file:`config.toml`
  #. :file:`.docbuild.config.toml`
  #. :file:`docbuild.config.toml`

  To bypass the automatic search and use an explicit file, pass the global ``--app-config`` option:

  .. code-block:: console

     $ docbuild --app-config /path/to/my-config.toml config list --app

Environment configuration
  Environment configuration files follow the pattern :file:`env.<role>.toml`, where ``<role>`` corresponds to an environment role such as ``production``, ``staging``, or ``devel`` (see :ref:`config-env-role`).

  * **Default file name:** :file:`env.production.toml` (loaded automatically when present in the search paths).
  * **Role-based file names:** :file:`env.<role>.toml` (for example, :file:`env.staging.toml` or :file:`env.devel.toml`).

  To select a specific environment configuration file, pass its path with the global ``--env-config`` option:

  .. code-block:: console

     $ docbuild --env-config env.devel.toml config list --env


.. _config-env-role:

Separating Environment Roles
----------------------------

Docbuild distinguishes a "role" of a configuration file. It can have these values:

* ``production``, ``prod``, or ``p``.
* ``staging``, ``stage`` or ``s``.
* ``testing``, ``t``, ``test``, ``dev``, or ``devel``.

Use separate TOML files to define the configuration for each of your environments. To avoid confusion, name each file according to its specific purpose. For instance, use :file:`env.devel.toml` for development, :file:`env.staging.toml` for staging, and :file:`env.production.toml` for production.

An example configuration file is provided in the repository at :gh_tree:`etc/docbuild/env.example.toml`.


Creating a new Configuration File
---------------------------------

To create a new configuration file, follow these steps one time:

#. In your cloned GitHub repository, copy the example file :file:`etc/docbuild/env.example.toml` to the root directory of this project. For example::

     cp etc/docbuild/env.example.toml env.devel.toml

#. Open your TOML file.

#. Adjust the path ``paths.root_config_dir``. Use the path from :ref:`get-xml-config`. Maybe adjust the key ``general.role``. The rest can stay as it is.

#. Specify this configuration file with the global option ``--env-config``.

Different ENV configuration files are important when you need to separate testing from production. To ease handling of different roles, refer to section :ref:`config-use-multiple-env-configs`.
