docbuild.cli.cmd_portal.cmd_list
================================

.. py:module:: docbuild.cli.cmd_portal.cmd_list

.. autoapi-nested-parse::

   Portal management commands for the docbuild CLI.



Functions
---------

.. autoapisummary::

   docbuild.cli.cmd_portal.cmd_list.build_hierarchy
   docbuild.cli.cmd_portal.cmd_list.parse_doctypes
   docbuild.cli.cmd_portal.cmd_list.get_display_name
   docbuild.cli.cmd_portal.cmd_list.append_translations
   docbuild.cli.cmd_portal.cmd_list.append_formats
   docbuild.cli.cmd_portal.cmd_list.append_categories
   docbuild.cli.cmd_portal.cmd_list.append_repo
   docbuild.cli.cmd_portal.cmd_list.build_deliverable_branch
   docbuild.cli.cmd_portal.cmd_list.print_hierarchy
   docbuild.cli.cmd_portal.cmd_list.async_list_cmd
   docbuild.cli.cmd_portal.cmd_list.list_cmd


Module Contents
---------------

.. py:function:: build_hierarchy(deliverables: list[docbuild.models.deliverable.Deliverable]) -> dict[str, dict[str, dict[str, list[docbuild.models.deliverable.Deliverable]]]]

   Group Deliverables into a hierarchy.

   :param deliverables: A list of Deliverable models to organize.
   :return: A hierarchy_dict mapping lang -> product -> docset -> deliverables.


.. py:function:: parse_doctypes(doctypes: tuple[str, Ellipsis], console: rich.console.Console) -> list[docbuild.models.doctype.Doctype] | None

   Parse raw CLI arguments into Doctype objects with default fallbacks.


.. py:function:: get_display_name(deliv: docbuild.models.deliverable.Deliverable, d_id: str) -> str

   Determine the main display name for a deliverable.


.. py:function:: append_translations(deliv_branch: rich.tree.Tree, deliv: docbuild.models.deliverable.Deliverable, lang: str) -> None

   Append translation metadata to the deliverable branch.


.. py:function:: append_formats(deliv_branch: rich.tree.Tree, deliv: docbuild.models.deliverable.Deliverable) -> None

   Append output formats metadata to the deliverable branch.


.. py:function:: append_categories(deliv_branch: rich.tree.Tree, deliv: docbuild.models.deliverable.Deliverable) -> None

   Append category metadata to the deliverable branch.


.. py:function:: append_repo(deliv_branch: rich.tree.Tree, deliv: docbuild.models.deliverable.Deliverable, repo_format: str) -> None

   Append repository metadata to the deliverable branch.


.. py:function:: build_deliverable_branch(docset_branch: rich.tree.Tree, deliv: docbuild.models.deliverable.Deliverable, lang: str, show_trans: bool, show_formats: bool, show_categories: bool, repo_format: str | None) -> None

   Format and append a single deliverable node to the Rich Tree.


.. py:function:: print_hierarchy(hierarchy: dict[str, dict[str, dict[str, list[docbuild.models.deliverable.Deliverable]]]], console: rich.console.Console, show_trans: bool, show_formats: bool, show_categories: bool, repo_format: str | None) -> None

   Render and print the nested hierarchy as a Rich Tree.


.. py:function:: async_list_cmd(ctx: docbuild.cli.context.DocBuildContext, doctypes: tuple[str, Ellipsis], console: rich.console.Console, show_trans: bool, show_formats: bool, show_categories: bool, repo_format: str | None) -> None
   :async:


   Async worker to fetch the XML, parse Doctypes, and build the tree.


.. py:function:: list_cmd(ctx: docbuild.cli.context.DocBuildContext, doctypes: tuple[str, Ellipsis], trans: bool, formats: bool, categories: bool, repo: str | None) -> None

   List products, docsets, and deliverables from the portal config.

   Accepts optional DOCTYPE arguments to filter the output.
   Format: PRODUCT/DOCSETS[@LIFECYCLES]/LANGS

   Example:
       docbuild portal list sles/15-SP6




   :param ctx: The DocBuildContext passed from the CLI, containing config and options.
   :param doctypes: A tuple of doctype strings passed as arguments to the command.
   :param trans: Show translation metadata.
   :param formats: Show output formats metadata.
   :param categories: Show categories metadata.
   :param repo: Show repository metadata (short or long).



