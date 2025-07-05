.. _configuring-docbuild:

Configuring the Tool
---------------------

Currently, the environment configuration is done via a TOML file. An example configuration file is provided in the repository. find it at :gh_tree:`etc/docbuild/env.example.toml`. Copy it to your working directory and name it accordingly to your purpose, for example, ``env.development.toml``, ``env.testing.toml``, or ``env.production.toml``. Modify it according to your needs.

To use the configuration file, specific it with the option ``--env-config``.

If you need to deal with different environments (testing, staging, production), it can be tedious to type. In such a case, use aliases in your shell.

.. code-block:: shell-session
   :caption: Example aliases for a configuration file
   :name: docbuild-aliases

   $ alias docbuild-prod='docbuild --env-config env.production.toml'
   $ alias docbuild-test='docbuild --env-config env.testing.toml'
   $ alias docbuild-dev='docbuild --env-config env.development.toml'

Keep in mind, all configuration files that match the pattern ``env.*.toml`` are ignored by git. This is on purpose to prevent accidental commits of sensitive information.