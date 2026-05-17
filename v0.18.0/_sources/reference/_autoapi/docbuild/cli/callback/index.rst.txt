docbuild.cli.callback
=====================

.. py:module:: docbuild.cli.callback

.. autoapi-nested-parse::

   Click callback to validate doctype strings.



Functions
---------

.. autoapisummary::

   docbuild.cli.callback.validate_doctypes


Module Contents
---------------

.. py:function:: validate_doctypes(ctx: click.Context, param: click.Parameter | None, doctypes: tuple[str, Ellipsis]) -> list[docbuild.models.doctype.Doctype]

   Click callback function to validate a list of doctype strings.

   Each string must conform to the format: PRODUCT/DOCSET@LIFECYCLE/LANGS
   LANGS can be a single language code, a comma-separated list (no spaces),
   or '*' for all.
   Defaults and wildcards (*) are handled.

   :param param: The click parameter that triggered this callback.
   :param doctypes: A tuple of doctype strings to validate.
   :return: A list of validated Doctype objects.
   :raises click.Abort: If any doctype string is invalid, the command is aborted.


