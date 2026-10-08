docbuild.cli.cmd_config.validate
================================

.. py:module:: docbuild.cli.cmd_config.validate

.. autoapi-nested-parse::

   CLI interface to validate the configuration files.



Functions
---------

.. autoapisummary::

   docbuild.cli.cmd_config.validate.validate


Module Contents
---------------

.. py:function:: validate(ctx: click.Context) -> None

   Validate TOML configuration files.

   This checks the syntax and schema of application and environment files.

   :param ctx: The Click context object, which should already have loaded configurations.


