.. _config-use-multiple-env-configs:

Using Multiple Environment Configurations
=========================================

To deal with different environments without having to type the full command
each time, create aliases in your shell. This allows you to quickly switch
between configurations without needing to remember the exact command syntax.

.. code-block:: shell-session
   :caption: Example aliases for different configuration files
   :name: docbuild-aliases

   $ alias docbuild-prod='docbuild --env-config env.production.toml'
   $ alias docbuild-test='docbuild --env-config env.testing.toml'
   $ alias docbuild-dev='docbuild --env-config env.devel.toml'
