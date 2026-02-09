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
   docbuild.cli.cmd_metadata.metaprocess.process_deliverable
   docbuild.cli.cmd_metadata.metaprocess.update_repositories
   docbuild.cli.cmd_metadata.metaprocess.process_doctype
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

   Group files by (Product, Docset).

   Yields (Doctype, Docset, List[Path]) using a flattened iteration strategy.


.. py:function:: process_deliverable(deliverable: docbuild.models.deliverable.Deliverable, *, repo_dir: pathlib.Path, tmp_repo_dir: pathlib.Path, base_cache_dir: pathlib.Path, meta_cache_dir: pathlib.Path, dapstmpl: str) -> bool
   :async:


   Process a single deliverable asynchronously.

   This function creates a temporary clone of the deliverable's repository,
   checks out the correct branch, and then executes the DAPS command to
   generate metadata.

   :param deliverable: The Deliverable object to process.
   :param repo_dir: The permanent repo path taken from the env
        config ``paths.repo_dir``
   :param tmp_repo_dir: The temporary repo path taken from the env
        config ``paths.tmp_repo_dir``
   :param base_cache_dir: The base path of the cache directory taken
        from the env config ``paths.base_cache_dir``
   :param meta_cache_dir: The ath of the metadata directory taken
        from the env config ``paths.meta_cache_dir``
   :param dapstmp: A template string with the daps command and potential
    placeholders
   :return: True if successful, False otherwise.
   :raises ValueError: If required configuration paths are missing.


.. py:function:: update_repositories(deliverables: list[docbuild.models.deliverable.Deliverable], bare_repo_dir: pathlib.Path) -> bool
   :async:


   Update all Git repositories associated with the deliverables.

   :param deliverables: A list of Deliverable objects.
   :param bare_repo_dir: The root directory for storing permanent bare clones.


.. py:function:: process_doctype(root: lxml.etree._ElementTree, context: docbuild.cli.context.DocBuildContext, doctype: docbuild.models.doctype.Doctype, *, exitfirst: bool = False, skip_repo_update: bool = False) -> list[docbuild.models.deliverable.Deliverable]
   :async:


   Process the doctypes and create metadata files.

   :param root: The stitched XML node containing configuration.
   :param context: The DocBuildContext containing environment configuration.
   :param doctypes: A tuple of Doctype objects to process.
   :param exitfirst: If True, stop processing on the first failure.
   :return: True if all files passed validation, False otherwise


.. py:function:: store_productdocset_json(context: docbuild.cli.context.DocBuildContext, doctypes: collections.abc.Sequence[docbuild.models.doctype.Doctype], stitchnode: lxml.etree._ElementTree) -> None

   Collect all JSON file for product/docset and create a single file.

   :param context: Beschreibung
   :param doctypes: Beschreibung
   :param stitchnode: Beschreibung


.. py:function:: process(context: docbuild.cli.context.DocBuildContext, doctypes: collections.abc.Sequence[docbuild.models.doctype.Doctype] | None, *, exitfirst: bool = False, skip_repo_update: bool = False) -> int
   :async:


   Asynchronous function to process metadata retrieval.

   :param context: The DocBuildContext containing environment configuration.
   :param doctype: A Doctype object to process.
   :param exitfirst: If True, stop processing on the first failure.
   :param skip_repo_update: If True, skip updating Git repositories before processing.
   :raises ValueError: If no envconfig is found or if paths are not
       configured correctly.
   :return: 0 if all files passed validation, 1 if any failures occurred.


