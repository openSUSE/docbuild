docbuild.cli.cmd_validate
=========================

.. py:module:: docbuild.cli.cmd_validate

.. autoapi-nested-parse::

   CLI interface to validate XML configuration files.



Submodules
----------

.. toctree::
   :maxdepth: 1

   /reference/_autoapi/docbuild/cli/cmd_validate/process/index


Functions
---------

.. autoapisummary::

   docbuild.cli.cmd_validate.validate


Package Contents
----------------

.. py:function:: validate(ctx: click.Context, xmlfiles: tuple | collections.abc.Iterator[pathlib.Path], validation_method: str) -> None

   Subcommand to validate XML configuration files.

   :param ctx: The Click context object.
   :param xmlfiles: XML files to validate, if empty all XMLs in config dir are used.
   :param validation_method: Validation method to use, 'jing' or 'lxml'.


