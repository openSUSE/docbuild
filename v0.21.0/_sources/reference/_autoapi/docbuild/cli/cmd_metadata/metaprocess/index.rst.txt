docbuild.cli.cmd_metadata.metaprocess
=====================================

.. py:module:: docbuild.cli.cmd_metadata.metaprocess

.. autoapi-nested-parse::

   Defines the handling of metadata extraction from deliverables.



Functions
---------

.. autoapisummary::

   docbuild.cli.cmd_metadata.metaprocess.get_deliverable_from_doctype
   docbuild.cli.cmd_metadata.metaprocess.collect_files_flat
   docbuild.cli.cmd_metadata.metaprocess.get_daps_command
   docbuild.cli.cmd_metadata.metaprocess.update_metadata_json
   docbuild.cli.cmd_metadata.metaprocess.process_deliverable
   docbuild.cli.cmd_metadata.metaprocess.update_repositories
   docbuild.cli.cmd_metadata.metaprocess.run_tasks_fail_fast
   docbuild.cli.cmd_metadata.metaprocess.run_tasks_collect_all
   docbuild.cli.cmd_metadata.metaprocess.process_doctype
   docbuild.cli.cmd_metadata.metaprocess.apply_parity_fixes
   docbuild.cli.cmd_metadata.metaprocess.load_and_validate_documents
   docbuild.cli.cmd_metadata.metaprocess.store_productdocset_json
   docbuild.cli.cmd_metadata.metaprocess.process


Module Contents
---------------

.. py:function:: get_deliverable_from_doctype(root: lxml.etree._ElementTree, doctype: docbuild.models.doctype.Doctype) -> list[docbuild.models.deliverable.Deliverable]

   Get deliverable from doctype.

   :param root: The stitched XML node containing configuration.
   :param doctype: The Doctype object to process.
   :return: A list of deliverables for the given doctype.


.. py:function:: collect_files_flat(doctypes: collections.abc.Sequence[docbuild.models.doctype.Doctype], basedir: pathlib.Path | str) -> collections.abc.Generator[tuple[docbuild.models.doctype.Doctype, str, list[pathlib.Path]], Any, None]

   Recursively collect all DC-metadata files from the cache directory.

   :param doctypes: Sequence of Doctype objects to filter by.
   :param basedir: The base directory to start the recursive search.
   :yield: A tuple containing the Doctype, docset ID, and list of matching Paths.


.. py:function:: get_daps_command(worktree_dir: pathlib.Path, dcfile_path: pathlib.Path, outputjson: pathlib.Path, dapstmpl: str) -> list[str]

   Construct the DAPS command for native execution.


.. py:function:: update_metadata_json(outputjson: pathlib.Path, deliverable: docbuild.models.deliverable.Deliverable) -> None

   Update the generated metadata JSON with deliverable-specific details.


.. py:function:: process_deliverable(context: docbuild.cli.context.DocBuildContext, deliverable: docbuild.models.deliverable.Deliverable, *, dapstmpl: str) -> tuple[bool, docbuild.models.deliverable.Deliverable]
   :async:


   Process a single deliverable asynchronously.

   This function creates a temporary clone of the deliverable's repository,
   checks out the correct branch, and then executes the DAPS command to
   generate metadata.

   :param context: The DocBuildContext containing environment configuration.
   :param deliverable: The Deliverable object to process.
   :param dapstmpl: A template string with the daps command and potential
    placeholders.
   :return: True if successful, False otherwise.


.. py:function:: update_repositories(deliverables: list[docbuild.models.deliverable.Deliverable], bare_repo_dir: pathlib.Path) -> bool
   :async:


   Update all Git repositories associated with the deliverables.

   :param deliverables: A list of Deliverable objects.
   :param bare_repo_dir: The root directory for storing permanent bare clones.


.. py:function:: run_tasks_fail_fast(tasks: list[asyncio.Task]) -> list[docbuild.models.deliverable.Deliverable]
   :async:


   Execute tasks and stop immediately on the first failure.


.. py:function:: run_tasks_collect_all(tasks: list[asyncio.Task], deliverables: list[docbuild.models.deliverable.Deliverable]) -> list[docbuild.models.deliverable.Deliverable]
   :async:


   Execute all tasks and collect every failure encountered.


.. py:function:: process_doctype(root: lxml.etree._ElementTree, context: docbuild.cli.context.DocBuildContext, doctype: docbuild.models.doctype.Doctype, *, exitfirst: bool = False, skip_repo_update: bool = False) -> list[docbuild.models.deliverable.Deliverable]
   :async:


   Process the doctypes and create metadata files.

   :param root: The stitched XML node containing configuration.
   :param context: The DocBuildContext containing environment configuration.
   :param doctype: The Doctype object to process.
   :param exitfirst: If True, stop processing on the first failure.
   :param skip_repo_update: If True, do not fetch updates for the git repositories.
   :return: A list of failed Deliverables.


.. py:function:: apply_parity_fixes(descriptions: list, categories: list) -> None

   Apply wording and HTML parity fixes for legacy JSON consistency.


.. py:function:: load_and_validate_documents(files: list[pathlib.Path], meta_cache_dir: pathlib.Path, manifest: docbuild.models.manifest.Manifest) -> None

   Load JSON metadata files and append validated Document models to the manifest.


.. py:function:: store_productdocset_json(context: docbuild.cli.context.DocBuildContext, doctypes: collections.abc.Sequence[docbuild.models.doctype.Doctype], stitchnode: lxml.etree._ElementTree) -> None

   Collect all JSON files for product/docset and create a single file.

   :param context: DocBuildContext object
   :param doctypes: Sequence of Doctype objects
   :param stitchnode: The stitched XML tree


.. py:function:: process(context: docbuild.cli.context.DocBuildContext, doctypes: collections.abc.Sequence[docbuild.models.doctype.Doctype] | None, *, exitfirst: bool = False, skip_repo_update: bool = False) -> int
   :async:


   Asynchronous function to process metadata retrieval.

   :param context: The DocBuildContext containing environment configuration.
   :param doctypes: A sequence of Doctype objects to process.
   :param exitfirst: If True, stop processing on the first failure.
   :param skip_repo_update: If True, skip updating Git repositories before processing.
   :raises ValueError: If no envconfig is found or if paths are not
       configured correctly.
   :return: 0 if all files passed validation, 1 if any failures occurred.


