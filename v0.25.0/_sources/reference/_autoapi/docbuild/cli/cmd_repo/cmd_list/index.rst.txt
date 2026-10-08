docbuild.cli.cmd_repo.cmd_list
==============================

.. py:module:: docbuild.cli.cmd_repo.cmd_list

.. autoapi-nested-parse::

   List the available permanent repositories.



Functions
---------

.. autoapisummary::

   docbuild.cli.cmd_repo.cmd_list.cmd_list


Module Contents
---------------

.. py:function:: cmd_list(ctx: click.Context) -> None

   List the available permanent repositories.

   Outputs the directory names of all repositories defined in the
   environment configuration.
   If no repositories are defined, it outputs a message indicating that
   no repositories are available.

   :param ctx: The Click context object.


