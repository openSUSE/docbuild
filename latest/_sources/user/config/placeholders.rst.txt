.. _config-placeholders:

Using Placeholders
==================

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

     [general]
     name = "doc-example-com"

     [paths]
     base_cache_dir = "/tmp/cache"
     base_server_cache_dir = "{base_cache_dir}/{general.name}"

  In this example, the key ``base_server_cache_dir`` uses the
  static placeholder ``{general.name}`` to reference the value of the
  key ``name`` in the ``general`` section.

  If you have nested sections, use dot notation to reference the keys (for example, ``section.subsection.key``).


Debugging Placeholders
----------------------

To inspect the configuration with placeholders left unresolved, use the ``-U`` or ``--unresolved`` flag with :command:`docbuild config list`. See :ref:`config-viewing-unresolved-placeholders`.
