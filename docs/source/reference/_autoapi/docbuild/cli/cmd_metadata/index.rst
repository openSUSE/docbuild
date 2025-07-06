docbuild.cli.cmd_metadata
=========================

.. py:module:: docbuild.cli.cmd_metadata

.. autoapi-nested-parse::

   Extracts metadata from deliverables.



Functions
---------

.. autoapisummary::

   docbuild.cli.cmd_metadata.get_deliverable_from_doctype
   docbuild.cli.cmd_metadata.process_deliverable
   docbuild.cli.cmd_metadata.process_doctype
   docbuild.cli.cmd_metadata.process
   docbuild.cli.cmd_metadata.metadata


Package Contents
----------------

.. py:function:: get_deliverable_from_doctype(root: lxml.etree._ElementTree, context: docbuild.cli.context.DocBuildContext, doctype: docbuild.models.doctype.Doctype) -> list[docbuild.models.deliverable.Deliverable]

   Get deliverable from doctype.

   :param root: The stitched XML node containing configuration.
   :param context: The DocBuildContext containing environment configuration.
   :param doctype: The Doctype object to process.
   :return: A list of deliverables for the given doctype.


.. py:function:: process_deliverable(deliverable: docbuild.models.deliverable.Deliverable, *, repo_dir: pathlib.Path, temp_repo_dir: pathlib.Path, base_cache_dir: pathlib.Path, meta_cache_dir: pathlib.Path, dapstmpl: str) -> bool
   :async:


   Process a single deliverable.

   This function creates a temporary clone of the deliverable's repository,
   checks out the correct branch, and then executes the DAPS command to
   generate metadata.

   :param deliverable: The Deliverable object to process.
   :param repo_dir: The permanent repo path taken from the env
        config ``paths.repo_dir``
   :param temp_repo_dir: The temporary repo path taken from the env
        config ``paths.temp_repo_dir``
   :param base_cache_dir: The base path of the cache directory taken
        from the env config ``paths.base_cache_dir``
   :param meta_cache_dir: The ath of the metadata directory taken
        from the env config ``paths.meta_cache_dir``
   :param dapstmp: A template string with the daps command and potential
    placeholders
   :return: True if successful, False otherwise.
   :raises ValueError: If required configuration paths are missing.


.. py:function:: process_doctype(root: lxml.etree._ElementTree, context: docbuild.cli.context.DocBuildContext, doctype: docbuild.models.doctype.Doctype) -> bool
   :async:


   Process the doctypes and create metadata files.

   :param root: The stitched XML node containing configuration.
   :param context: The DocBuildContext containing environment configuration.
   :param doctypes: A tuple of Doctype objects to process.


.. py:function:: process(context: docbuild.cli.context.DocBuildContext, doctypes: tuple[docbuild.models.doctype.Doctype]) -> int
   :async:


   Asynchronous function to process metadata retrieval.

   :param context: The DocBuildContext containing environment configuration.
   :param xmlfiles: A tuple or iterator of XML file paths to validate.
   :raises ValueError: If no envconfig is found or if paths are not
       configured correctly.
   :return: 0 if all files passed validation, 1 if any failures occurred.


.. py:function:: metadata(ctx: click.Context, doctypes: tuple[docbuild.models.doctype.Doctype]) -> None

   Subcommand to create metadata files.

   :param ctx: The Click context object.


