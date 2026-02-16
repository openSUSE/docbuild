Showing Configuration
=====================

The docbuild tool distinguishes between two types of configuration files:

* Application configuration files ("app config")

* Environment configuration files ("env config")

Additionally, the docbuild tool has also hardcoded default values for both types of configuration.

If no env or app configuration files are found, the docbuild tool will
fallback to these hardcoded default values.

Keep in mind that these defaults may not be suitable for all use cases, and it is recommended to create and use a configuration file to customize the behavior of the docbuild tool.


.. admonition:: TOML as default format

   Both configuration types are written in TOML format, which is a human-readable data serialization standard. See `TOML docs <https://toml.io/en/>`_ for more information on its syntax and structure.

The following subsections provide more details on how to view and manage the configuration files for both application and environment settings.


.. toctree::
   :maxdepth: 2

   application
   environment
