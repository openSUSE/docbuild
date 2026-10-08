Validating Configuration
========================

The :command:`docbuild config validate` subcommand is used to verify that your TOML configuration files are syntactically correct and conform to the required schema.

.. code-block:: shell
   :caption: Synopsis of :command:`docbuild config validate`

   $ docbuild config validate [OPTIONS]

The tool validates:

1. **Application Configuration**: Ensures core settings like logging and worker limits are valid.
2. **Environment Configuration**: Checks paths, server roles, and build parameters.

Options
-------

* ``--app``: Validate only the application configuration.
* ``--env``: Validate only the environment configuration.
* ``--all``: Validate everything (default).

.. note::
   For validating Portal XML configuration files, use :ref:`validate-portal` (:command:`docbuild portal validate`).
