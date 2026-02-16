.. _config-docbuild:

Configuring the Tool
---------------------

.. note::

   To prevent accidental commits of sensitive information, all configuration files matching the :file:`env.*.toml` pattern in the root directory are ignored by Git. However, this rule does not apply to files within the :file:`etc/` directory.

Use separate TOML files to define the configuration for each of your environments. To avoid confusion, name each file according to its specific purpose. For instance, use :file:`env.devel.toml` for development, :file:`env.staging.toml` for staging, and :file:`env.production.toml` for production.

An example configuration file is provided in the repository at :gh_tree:`etc/docbuild/env.example.toml`.

To use your configuration file, follow these steps one time:

#. In your cloned GitHub repository, copy the example file :file:`etc/docbuild/env.example.toml` to the root directory of this project. For example::

     cp etc/docbuild/env.example.toml env.devel.toml

#. Open your TOML file.

#. Adjust the path ``paths.root_config_dir``. Use the path from :ref:`get-xml-config`. The rest can stay as it is.

#. Specify the configuration with the global option ``--env-config``.


.. _config-key-naming-conventions:

Key Naming Conventions
----------------------

The keys follow specific naming conventions to indicate their purpose and expected value types. Here are some common patterns whereas the asterisk
(``*``) represents a variable part of the key:

* ``*_dir``: Contains a directory.

* ``tmp_*``: Indicates a temporary path.

* ``*_dyn``: Denotes a dynamic value that is expected to be resolved at runtime.

Directories are created automatically when the script runs. Additionally,
the script checks if the specified paths are readable, writeable and belongs
to the user running the script.


.. _config-validation:

Validating the Configuration
-----------------------------

Before docbuild executes any commands, it validates the provided configuration
file against a predefined :term:`Pydantic` model.

The validation checks for different aspects of the configuration, such as:

* Presence of mandatory keys.
* Correct data types (for example, strings, integers, lists).
* Valid paths and if they exist on the filesystem and are writable when
  required.
* Correct use of placeholders.


..
   TODO: Add a link to the TOML env config reference, add an example of
   a validation error message, and explain how to fix common issues.
   a validation error message, and explain how to fix common issues.


.. _config-placeholders:

Using Placeholders
------------------

Docbuild supports the use of placeholders in the configuration file.
Two types of placeholders are supported:

* **Static placeholders** (Syntax ``{placeholder}``)

  They are used to reference *other parts* of the configuration.
  For example, assume you have a configuration key ``paths.root_config_dir`` that defines the root directory for configuration files. You can use a static placeholder like ``{paths.root_config_dir}`` in other parts of the configuration to refer to this value.

  This allows you to maintain consistency and avoid repeating the same path multiple times in your configuration file.


* **Dynamic placeholders** (Syntax ``{{placeholder}}``)

  These types of placeholder cannot and must not be replaced. They are meant to be used as *templates* for values that will be resolved at runtime. For example, you might have a placeholder like ``{{product}}`` that is intended to be replaced with the actual product name when the docbuild tool runs.

  This allows for greater flexibility and adaptability in your configuration, as the same configuration file can be used across different products or environments without needing to hardcode specific values.

These types of placeholder make it easier to manage and maintain your configuration files, as they allow you to centralize key values and create reusable templates for dynamic content.

Static placeholders follow a specific syntax:

* **Regular name** (Syntax ``{placeholder}``)

  A regular name refers to another key in the same section:

  .. code-block:: toml
     :emphasize-lines: 3

     [paths]
     root_config_dir = "~/repos/GL/susedoc/docserv-config"
     jinja_dir = "{root_config_dir}/jinja-doc-suse-com"

  In the previous example, the key ``jinja_dir`` uses a static placeholder
  ``{root_config_dir}`` to reference the value of the same key
  ``root_config_dir`` within the same section.

* **Section name** (Syntax ``{section.key}``)

  A section name refers to a key in another section:

  .. code-block:: toml
     :emphasize-lines: 5

     [server]
     name = "doc-example-com"

     [paths]
     base_cache_dir = "/tmp/cache"
     base_server_cache_dir = "{base_cache_dir}/{server.name}"
     base_server_cache_dir = "{base_cache_dir}/{server.name}"

  In this example, the key ``base_server_cache_dir`` uses the
  static placeholder ``{server.name}`` to reference the value of the
  key ``name`` in the ``server`` section.

  If you have nested sections, use dot notation to reference the keys (for example, ``section.subsection.key``).


.. _config-viewing-docbuild-config-env:

Viewing the Environment Configuration
-------------------------------------

To see how ``docbuild`` interprets your environment configuration, use the
``config env`` subcommand. This is particularly useful for verifying that all
static placeholders have been correctly resolved into absolute paths.

.. code-block:: shell-session
   :caption: Displaying the resolved environment configuration

   docbuild --env-config=YOUR_TOML_CONFIG config env

If the configuration contains errors—such as missing mandatory keys or invalid data types—the command will output a validation error detailing what needs to be fixed.


.. _config-use-multiple-env-configs:

Using Multiple Environment Configurations
-----------------------------------------

To deal with different environments without having to type the full command
each time, create aliases in your shell. This allows you to quickly switch
between configurations without needing to remember the exact command syntax.

.. code-block:: shell-session
   :caption: Example aliases for different configuration files
   :name: docbuild-aliases

   alias docbuild-prod='docbuild --env-config env.production.toml'
   alias docbuild-test='docbuild --env-config env.testing.toml'
   alias docbuild-dev='docbuild --env-config env.devel.toml'
