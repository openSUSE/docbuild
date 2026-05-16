docbuild.cli.cmd_portal.process
===============================

.. py:module:: docbuild.cli.cmd_portal.process

.. autoapi-nested-parse::

   Module for processing XML validation in DocBuild.



Classes
-------

.. toctree::
   :hidden:

   /reference/_autoapi/docbuild/cli/cmd_portal/process/ValidationResult

.. autoapisummary::

   docbuild.cli.cmd_portal.process.ValidationResult


Functions
---------

.. autoapisummary::

   docbuild.cli.cmd_portal.process.display_results
   docbuild.cli.cmd_portal.process.validate_rng
   docbuild.cli.cmd_portal.process.run_python_checks
   docbuild.cli.cmd_portal.process.run_validation
   docbuild.cli.cmd_portal.process.parse_portal_config
   docbuild.cli.cmd_portal.process.run_checks_and_display
   docbuild.cli.cmd_portal.process.cache_resolved_portal_config
   docbuild.cli.cmd_portal.process.process


Module Contents
---------------

.. py:function:: display_results(check_results: list[tuple[str, docbuild.config.xml.checks.CheckResult]], summary_line: str | None = None, tree: lxml.etree._ElementTree | None = None) -> None

   Display Stage 2 (Python checks) results using rich.

   Errors are always printed regardless of verbosity.

   :param check_results: List of tuples containing check names and their results.
   :param summary_line: Optional preformatted stage summary line.
   :param tree: Optional parsed XML tree used to resolve ``xml:base`` filenames.


.. py:function:: validate_rng(xmlfile: pathlib.Path, rng_schema_path: pathlib.Path, *, xinclude: bool = True, idcheck: bool = True) -> subprocess.CompletedProcess
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


.. py:function:: run_python_checks(tree: lxml.etree._ElementTree) -> list[tuple[str, docbuild.config.xml.checks.CheckResult]]
   :async:


   Run all registered Python-based checks against a parsed XML tree.

   :param tree: The parsed XML element tree.
   :return: A list of tuples containing check names and their results.


.. py:function:: run_validation(filepath: pathlib.Path | str, schema_path: pathlib.Path) -> ValidationResult
   :async:


   Run RNG validation using the selected method and normalize result.

   :param filepath: Path to the XML file to validate.
   :param schema_path: Path to the RNG schema.
   :returns: A :class:`ValidationResult` describing the outcome.


.. py:function:: parse_portal_config(filepath: pathlib.Path | str) -> lxml.etree._ElementTree
   :async:


   Parse XML file using lxml in a background thread.

   Exceptions from :func:`lxml.etree.parse` (for example
   :class:`lxml.etree.XMLSyntaxError`) are propagated to the caller.

   :param filepath: Path to the XML file to parse.
   :returns: Parsed :class:`lxml.etree._ElementTree`.


.. py:function:: run_checks_and_display(tree: lxml.etree._ElementTree, context: docbuild.cli.context.DocBuildContext) -> bool
   :async:


   Execute registered Python checks and print formatted results.

   :param tree: Parsed XML tree to check.
   :param context: :class:`DocBuildContext` used to read verbosity.
   :returns: True when all checks succeeded (or when no checks are registered).


.. py:function:: cache_resolved_portal_config(context: docbuild.cli.context.DocBuildContext, tree: lxml.etree._ElementTree, main_portal_config: pathlib.Path) -> pathlib.Path | None
   :async:


   Write the resolved portal XML to cache when a cache directory is configured.

   :param context: The active DocBuild context.
   :param tree: Parsed portal XML tree, potentially with resolved XIncludes.
   :param main_portal_config: Path of the main portal XML configuration file.
   :returns: The cached XML path when written, otherwise ``None``.


.. py:function:: process(context: docbuild.cli.context.DocBuildContext, main_portal_config: pathlib.Path, portal_schema: pathlib.Path) -> int
   :async:


   Asynchronous function to process validation.

   :param context: The DocBuildContext containing environment configuration.
   :param main_portal_config: Path to the main Portal XML configuration file.
   :param portal_schema: Path to the Portal RELAX NG schema file.
   :raises ValueError: If no envconfig is found.
   :return: 0 if validation passed, 1 if any failures occurred.


