docbuild.cli.cmd_build
======================

.. py:module:: docbuild.cli.cmd_build

.. autoapi-nested-parse::

   CLI interface to build a document.

   A document (or "doctype") consists of ``[PRODUCT]/[DOCSET][@LIFECYCLES]/LANGS``
   with the following properties:

   

   * (Optional) ``PRODUCT`` is the product. To mark "ALL" products, omit the
     product or use "*"
   * (Optional) ``DOCSET`` is the docset, usually the version or release of
     a product.
     To mark "ALL" docsets, omit the docset or use ``"*"``.
   * (Optional) ``LIFECYCLES`` marks a list of lifecycles separated by comma
     or pipe symbol.
     A lifecycle can be one of the values 'supported', 'unsupported', 'beta',
     or 'hidden'.
   * ``LANGS`` marks a list of languages separated by comma. Every single
     language contains a LANGUAGE-COUNTRY syntax, for example 'en-us', 'de-de' etc.

   Examples of the doctypes syntax:

   

   * ``"//en-us"``
     Builds all supported deliverables for English
   * ``"sles/*/en-us"``
     Builds only SLES deliverables which are supported and in English
   * ``"sles/*@unsupported/en-us,de-de"``
     Builds all English and German SLES releases which are unsupported
   * ``"sles/@beta|supported/de-de"``
     Build all docsets that are supported and beta for German SLES.
   * ``"sles/@beta,supported/de-de"``
     Same as the previous one, but with comma as the separator between
     the lifecycle states.



Functions
---------

.. autoapisummary::

   docbuild.cli.cmd_build.validate_doctypes
   docbuild.cli.cmd_build.build


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


.. py:function:: build(ctx: click.Context, doctypes: tuple[docbuild.models.doctype.Doctype]) -> None

   Subcommand build.

   :param ctx: The Click context object.
   :param doctypes: A tuple of doctype objects to build.


