docbuild.cli.cmd_portal.cmd_validate
====================================

.. py:module:: docbuild.cli.cmd_portal.cmd_validate

.. autoapi-nested-parse::

   Validate Portal XML configuration.



Functions
---------

.. autoapisummary::

   docbuild.cli.cmd_portal.cmd_validate.validate


Module Contents
---------------

.. py:function:: validate(ctx: click.Context, main_portal_config: pathlib.Path, portal_schema: pathlib.Path) -> None

   Subcommand to validate XML configuration files.

   :param ctx: The Click context object.
   :param main_portal_config: main Portal XML config file to validate.
   :param portal_schema: Portal schema file to use for validation.


