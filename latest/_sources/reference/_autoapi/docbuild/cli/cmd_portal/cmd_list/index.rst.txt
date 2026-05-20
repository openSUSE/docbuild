docbuild.cli.cmd_portal.cmd_list
================================

.. py:module:: docbuild.cli.cmd_portal.cmd_list

.. autoapi-nested-parse::

   Portal management commands for the docbuild CLI.



Functions
---------

.. autoapisummary::

   docbuild.cli.cmd_portal.cmd_list.build_hierarchy
   docbuild.cli.cmd_portal.cmd_list.async_list_cmd
   docbuild.cli.cmd_portal.cmd_list.list_cmd


Module Contents
---------------

.. py:function:: build_hierarchy(deliverables: list[docbuild.models.deliverable.Deliverable]) -> dict[str, dict[str, dict[str, list[str]]]]

   Group a list of Deliverable domain objects into a nested dictionary structure.

   :param deliverables: A list of Deliverable models to organize.
   :return: A nested dictionary structured as {lang: {product: {docset: [deliverable titles]}}}.


.. py:function:: async_list_cmd(ctx: docbuild.cli.context.DocBuildContext, doctypes: tuple[str, Ellipsis], console: rich.console.Console) -> None
   :async:


   Async worker to fetch the XML, parse Doctypes, and build the tree.

   :param ctx: The DocBuildContext containing CLI options and config.
   :param doctypes: A tuple of doctype strings passed as arguments to the command.
   :param console: The Rich Console object for outputting the tree.


.. py:function:: list_cmd(ctx: docbuild.cli.context.DocBuildContext, doctypes: tuple[str, Ellipsis]) -> None

   List products, docsets, and deliverables from the portal config.

   Accepts optional DOCTYPE arguments to filter the output.
   Format: [PRODUCT]/[DOCSETS]@[LIFECYCLES]/[LANGS]

   Example:
       docbuild portal list sles/15-SP6




   :param ctx: The DocBuildContext passed from the CLI, containing config and options.
   :param doctypes: A tuple of doctype strings passed as arguments to the command.



