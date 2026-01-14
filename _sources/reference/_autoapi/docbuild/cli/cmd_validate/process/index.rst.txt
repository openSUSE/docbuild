docbuild.cli.cmd_validate.process
=================================

.. py:module:: docbuild.cli.cmd_validate.process

.. autoapi-nested-parse::

   Module for processing XML validation in DocBuild.



Classes
-------

.. toctree::
   :hidden:

   /reference/_autoapi/docbuild/cli/cmd_validate/process/ValidationResult

.. autoapisummary::

   docbuild.cli.cmd_validate.process.ValidationResult


Functions
---------

.. autoapisummary::

   docbuild.cli.cmd_validate.process.display_results
   docbuild.cli.cmd_validate.process.validate_rng
   docbuild.cli.cmd_validate.process.validate_rng_lxml
   docbuild.cli.cmd_validate.process.run_python_checks
   docbuild.cli.cmd_validate.process.build_shortname
   docbuild.cli.cmd_validate.process.run_validation
   docbuild.cli.cmd_validate.process.parse_tree
   docbuild.cli.cmd_validate.process.run_checks_and_display
   docbuild.cli.cmd_validate.process.process_file
   docbuild.cli.cmd_validate.process.process


Module Contents
---------------

.. py:function:: display_results(shortname: str, check_results: list[tuple[str, docbuild.config.xml.checks.CheckResult]], verbose: int, max_len: int) -> None

   Display validation results based on verbosity level using rich.

   :param shortname: Shortened name of the XML file being processed.
   :param check_results: List of tuples containing check names and their results.
   :param verbose: Verbosity level (0, 1, 2)
   :param max_len: Maximum length for formatting the output.


.. py:function:: validate_rng(xmlfile: pathlib.Path, rng_schema_path: pathlib.Path = PRODUCT_CONFIG_SCHEMA, *, xinclude: bool = True, idcheck: bool = True) -> subprocess.CompletedProcess
   :async:


   Validate an XML file against a RELAX NG schema using jing.

   If `xinclude` is True (the default), this function resolves XIncludes by
   running `xmllint --xinclude` and piping its output to `jing`. This is
   more robust for complex XInclude statements, including those with XPointer.

   :param xmlfile: The path to the XML file to validate.
   :param rng_schema_path: The path to the RELAX NG schema file.
       It supports both RNC and RNG formats.
   :param xinclude: If True, resolve XIncludes with `xmllint` before validation.
   :param idcheck: If True, perform ID uniqueness checks.
   :return: A tuple containing a boolean success status and any output message.


.. py:function:: validate_rng_lxml(xmlfile: pathlib.Path, rng_schema_path: pathlib.Path = PRODUCT_CONFIG_SCHEMA) -> tuple[bool, str]

   Validate an XML file against a RELAX NG (.rng) schema using lxml.

   This function uses lxml.etree.RelaxNG, which supports only the XML syntax
   of RELAX NG schemas (i.e., .rng files, not .rnc files).

   :param xmlfile: Path to the XML file to validate.
   :param rng_schema_path: Path to the RELAX NG (.rng) schema file.
   :return: Tuple of (is_valid: bool, error_message: str)


.. py:function:: run_python_checks(tree: lxml.etree._ElementTree) -> list[tuple[str, docbuild.config.xml.checks.CheckResult]]
   :async:


   Run all registered Python-based checks against a parsed XML tree.

   :param tree: The parsed XML element tree.
   :return: A list of tuples containing check names and their results.


.. py:function:: build_shortname(filepath: pathlib.Path | str) -> str

   Return a shortened display name for ``filepath``.

   :param filepath: Path-like object to shorten.
   :returns: Shortened display name (last two path components or full path).


.. py:function:: run_validation(filepath: pathlib.Path | str, method: str) -> ValidationResult
   :async:


   Run RNG validation using the selected method and normalize result.

   :param filepath: Path to the XML file to validate.
   :param method: Validation method name ("jing" or "lxml").
   :returns: A :class:`ValidationResult` describing the outcome.


.. py:function:: parse_tree(filepath: pathlib.Path | str) -> lxml.etree._ElementTree
   :async:


   Parse XML file using lxml in a background thread.

   Exceptions from :func:`lxml.etree.parse` (for example
   :class:`lxml.etree.XMLSyntaxError`) are propagated to the caller.

   :param filepath: Path to the XML file to parse.
   :returns: Parsed :class:`lxml.etree._ElementTree`.


.. py:function:: run_checks_and_display(tree: lxml.etree._ElementTree, shortname: str, context: docbuild.cli.context.DocBuildContext, max_len: int) -> bool
   :async:


   Execute registered Python checks and print formatted results.

   :param tree: Parsed XML tree to check.
   :param shortname: Short name used for display output.
   :param context: :class:`DocBuildContext` used to read verbosity.
   :param max_len: Maximum length used for aligned output.
   :returns: True when all checks succeeded (or when no checks are registered).


.. py:function:: process_file(filepath: pathlib.Path | str, context: docbuild.cli.context.DocBuildContext, max_len: int) -> int
   :async:


   Process a single file: RNG validation then Python checks.

   :param filepath: The path to the XML file to process.
   :param context: The DocBuildContext.
   :param max_len: Maximum length for formatting the output.
   :param rng_schema_path: Optional path to an RNG schema for validation.
   :return: An exit code (0 for success, non-zero for failure).


.. py:function:: process(context: docbuild.cli.context.DocBuildContext, xmlfiles: tuple[pathlib.Path | str, Ellipsis] | collections.abc.Iterator[pathlib.Path]) -> int
   :async:


   Asynchronous function to process validation.

   :param context: The DocBuildContext containing environment configuration.
   :param xmlfiles: A tuple or iterator of XML file paths to validate.
   :raises ValueError: If no envconfig is found or if paths are not
       configured correctly.
   :return: 0 if all files passed validation, 1 if any failures occurred.


