docbuild.cli.cmd_config.list
============================

.. py:module:: docbuild.cli.cmd_config.list

.. autoapi-nested-parse::

   CLI interface to list the configuration.



Functions
---------

.. autoapisummary::

   docbuild.cli.cmd_config.list.print_section
   docbuild.cli.cmd_config.list.list_config


Module Contents
---------------

.. py:function:: print_section(title: str, data: dict[str, Any], prefix: str, flat: bool, color: str) -> None

   Print a configuration section in either flat or JSON format.


.. py:function:: list_config(ctx: click.Context, app: bool, env: bool, flat: bool) -> None

   List the configuration as JSON or flat text.


