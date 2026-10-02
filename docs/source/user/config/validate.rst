.. _validate-config:

Validating Configuration
========================

Before ``docbuild`` executes commands that consume configuration, it validates
the provided configuration files against predefined :term:`Pydantic` models.
The ``config list`` command skips validation unless you pass ``--validate``.

The validation checks for different aspects of the configuration, such as:

* Presence of mandatory keys.
* Correct data types (for example, strings, integers, lists).
* Valid paths and if they exist on the filesystem and are writable when
  required.
* Correct use of placeholders.


To ensure your TOML files match the required schema:

.. code-block:: shell

   $ docbuild config validate
   Running Configuration Validation...

   ✅ Application Configuration: Valid
     - /home/tux/repos/GH/opensuse/docbuild/.config.toml

   ✅ Environment Configuration: Valid
     - Using internal defaults
   ╭───────────────────────────────────────────╮
   │ Configuration is valid!                   │
   │ All TOML files match the required schema. │
   ╰───────────────────────────────────────────╯

This checks both application and environment files.


Detailed Validation Feedback
----------------------------

If the configuration is invalid, the application provides a structured,
color-coded error report to help you identify and fix the issues. Each error
includes:

* **Location**: The exact path in the TOML file (e.g., ``general.enable_mail``).
* **Field Info**: A human-readable title and description of the field's purpose.
* **Error Detail**: A specific message explaining why the value failed validation.
* **Documentation Link**: A direct URL to a reference page with more details
  on how to resolve that specific error type.

Example error output:

.. code-block:: text

    1 Validation error in config file 'env.devel.toml':

    (1) In 'general.enable_mail':
        Input should be a valid boolean, unable to interpret input
        Expected: Enable Email
        Description: Flag to enable email sending features.
        See: https://opensuse.github.io/docbuild/latest/errors/bool_parsing.html


Fixing Common Issues
--------------------

If you encounter validation errors, check the following common causes:

* **Missing Keys**: Ensure all mandatory fields (like ``paths.root_config_dir``) are defined.
* **Typing Errors**: Ensure booleans (``true``/``false``) and integers are not enclosed
  in quotes.
* **Permission Issues**: If a path error occurs, verify that the user running
  ``docbuild`` has the necessary read/write permissions for the specified directory.
* **Circular Placeholders**: Ensure that your static placeholders do not point
  to each other in a loop (e.g., Key A referencing Key B, which references Key A).
