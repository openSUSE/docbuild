Showing Env's Configuration
===========================

Environment configuration files ("env config") is specific to the environment in which the docbuild tool operates, such as paths to source files, output directories, and other environment-specific settings.

The tool looks for the configuration :file:`env.production.toml` in the current working directory.

If you want to override the default, use the ``--env-config`` option to specify a custom configuration file path.

.. code-block:: shell-session
   :caption: Showing env configuration content

   docbuild --env-config env.develop.toml config env
   # ENV Config file '/home/tux/repos/GH/opensuse/docbuild/env.production.toml'
   [ ... content ...]

In the previous example, there is a :file:`env.production.toml` file in the
current project's directory.

.. note::

   An example of an environment configuration file is provided in this repo
   in the :gh_path:`etc/docbuild/env.example.toml` directory.