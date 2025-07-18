.. _configuring-docbuild:

Configuring the Tool
---------------------

.. note::

   To prevent accidental commits of sensitive information, all configuration files matching the :file:`env.*.toml` pattern in the root directory are ignored by git. However, this rule does not apply to files within the :file:`etc/` directory.

Use separate TOML files to define the configuration for each of your environments. To avoid confusion, name each file according to its specific purpose. For instance, use :file:`env.devel.toml` for development, :file:`env.staging.toml` for staging, and :file:`env.production.toml` for production.

An example configuration file is provided in the repository at :gh_tree:`etc/docbuild/env.example.toml`.

To use your configuration file, follow these steps one time:

#. In your cloned GitHub repository, copy the example file :file:`etc/docbuild/env.example.toml` to the root directory of this project. For example::

     cp etc/docbuild/env.example.toml env.devel.toml

#. Open your TOML file.

#. Adjust the path ``paths.root_config_dir``. Use the path from :ref:`get-xml-config`. The rest can stay as it is.

#. Specific the configuration with the global option ``--env-config``.

To deal with different environments without having to type the full command each time, create aliases in your shell. This allows you to quickly switch between configurations without needing to remember the exact command syntax.

.. code-block:: shell-session
   :caption: Example aliases for different configuration files
   :name: docbuild-aliases

   $ alias docbuild-prod='docbuild --env-config env.production.toml'
   $ alias docbuild-test='docbuild --env-config env.testing.toml'
   $ alias docbuild-dev='docbuild --env-config env.devel.toml'
