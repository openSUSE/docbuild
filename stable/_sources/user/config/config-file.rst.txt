.. _config-tomlfile:


Using a TOML Configuration File
===============================

.. note::

   To prevent accidental commits of sensitive information, all configuration files matching the :file:`env.*.toml` pattern in the root directory are ignored by Git. However, this rule does not apply to files within the :file:`etc/` directory.


Configuration Places
--------------------

By default, Docbuild starts with its built-in values and looks for
:file:`env.production.toml` in the current working directory. If that file
exists, its values override the built-ins. To use a different file or role,
pass its path with the global ``--env-config`` option.

You do not require a configuration file. If the hard-coded values are fine for your task, go for it! If you only need to set one or two values, it may be easier to :ref:`overwrite config options <config-overwriting-cli>`.

To get an overview of the hard-coded values, refer to section :ref:`config-viewing-docbuild-config-env`.


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
