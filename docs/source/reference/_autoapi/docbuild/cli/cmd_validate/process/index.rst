docbuild.cli.cmd_validate.process
=================================

.. py:module:: docbuild.cli.cmd_validate.process

.. autoapi-nested-parse::

   Module for processing XML validation in DocBuild.



Functions
---------

.. autoapisummary::

   docbuild.cli.cmd_validate.process.display_results
   docbuild.cli.cmd_validate.process.run_command
   docbuild.cli.cmd_validate.process.validate_rng
   docbuild.cli.cmd_validate.process.run_python_checks
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


.. py:function:: run_command(*args: str, env: dict[str, str] | None = None) -> tuple[int, str, str]
   :async:


   Run an external command and capture its output.

   :param args: The command and its arguments separated as tuple elements.
   :param env: A dictionary of environment variables for the new process.
   :return: A tuple of (returncode, stdout, stderr).
   :raises FileNotFoundError: if the command is not found.


.. py:function:: validate_rng(xmlfile: pathlib.Path, rng_schema_path: pathlib.Path = PRODUCT_CONFIG_SCHEMA, *, xinclude: bool = True) -> tuple[bool, str]
   :async:


   Validate an XML file against a RELAX NG schema using jing.

   If `xinclude` is True (the default), this function resolves XIncludes by
   running `xmllint --xinclude` and piping its output to `jing`. This is
   more robust for complex XInclude statements, including those with XPointer.

   :param xmlfile: The path to the XML file to validate.
   :param rng_schema_path: The path to the RELAX NG schema file. It supports
       both RNC and RNG formats.
   :param xinclude: If True, resolve XIncludes with `xmllint` before validation.
   :return: A tuple containing a boolean success status and any output message.


.. py:function:: run_python_checks(tree: lxml.etree._ElementTree) -> list[tuple[str, docbuild.config.xml.checks.CheckResult]]
   :async:


   Run all registered Python-based checks against a parsed XML tree.

   :param tree: The parsed XML element tree.
   :return: A list of tuples containing check names and their results.


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


