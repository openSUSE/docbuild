Showing App's Configuration
===========================

Application configuration files ("app config") affects the behavior of the docbuild tool itself, such as how it processes documents, logging, handles errors, etc.

The tool can read these configuration files in different locations in the following order:

* In the system configuration directory, typically located at ``/etc/docbuild/`` (lowest priority).
* In the user configuration directory, typically located at ``~/.config/docbuild/``.
* In the current working directory, where the docbuild tool is executed, at ``.`` (highest priority).

In each of these location, the tool will look for configuration files named :file:`.config.toml` or :file:`config.toml`. Additionally, the tool will
merge the configuration from these files. Higher priority files will override the settings of lower priority files.

If you want to override the default search strategy, use the ``--app-config`` option to specify a custom configuration file path.

.. code-block:: shell-session
   :caption: Showing configuration files

   $ docbuild config app
   # Application config files '/home/tux/repos/GH/opensuse/docbuild/.config.toml'
   [ ... content ...]

In the previous example, there is a :file:`.config.toml` file in the
current project's directory.