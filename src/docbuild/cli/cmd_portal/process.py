"""Module for processing XML validation in DocBuild."""

import asyncio
from dataclasses import dataclass
import logging
from pathlib import Path
from subprocess import CompletedProcess

from lxml import etree
from rich.console import Console
from rich.markup import escape

from ...config.xml.checks import CheckResult, register_check
from ...config.xml.xinclude import parse_xml_with_xinclude_base
from ...utils.decorators import RegistryDecorator
from ...utils.shell import run_command
from ..context import DocBuildContext

# Cast to help with type checking
registry: RegistryDecorator = register_check  # type: ignore[assignment]

# Set up logging
log = logging.getLogger(__name__)

# Set up rich consoles for output
console_out = Console()
console_err = Console(stderr=True)


XINCLUDE_PROP = (
    "-D"
    #
    "org.apache.xerces.xni.parser.XMLParserConfiguration="
    "org.apache.xerces.parsers.XIncludeParserConfiguration"
)

XML_BASE_ATTR = "{http://www.w3.org/XML/1998/namespace}base"


def _filename_from_xml_base(
    tree: etree._ElementTree,
    xpath: str,
) -> str | None:
    """Resolve nearest ancestor ``xml:base`` filename for a matched XPath node."""
    try:
        matches = tree.xpath(xpath)
    except (etree.XPathError, TypeError):
        return None

    if not matches:
        return None

    node = matches[0]
    if not isinstance(node, etree._Element):
        return None

    current: etree._Element | None = node
    while current is not None:
        xml_base = current.get(XML_BASE_ATTR)
        if xml_base:
            return xml_base
        current = current.getparent()

    return None


def display_results(
    check_results: list[tuple[str, CheckResult]],
    summary_line: str | None = None,
    tree: etree._ElementTree | None = None,
) -> None:
    """Display Stage 2 (Python checks) results using rich.

    Errors are always printed regardless of verbosity.

    :param check_results: List of tuples containing check names and their results.
    :param summary_line: Optional preformatted stage summary line.
    :param tree: Optional parsed XML tree used to resolve ``xml:base`` filenames.
    """
    failed_checks = []

    for check_name, result in check_results:
        if not result.success:
            failed_checks.append((check_name, result))

    if summary_line:
        console_out.print(summary_line)

    # Always print error details, independent of verbosity
    for idx, (check_name, result) in enumerate(failed_checks, start=1):
        if idx > 1:
            console_err.print("")
        console_err.print(f"[bold red]{idx}. ✗ {check_name}:[/bold red]")
        for message in result.messages:
            console_err.print(message)
        if result.xpath:
            console_err.print(f"  XPath: {escape(result.xpath)}")
        if tree is not None:
            filename = _filename_from_xml_base(tree, result.xpath)
            if filename:
                console_err.print(f"  File: {filename}")


async def validate_rng(
    xmlfile: Path,
    rng_schema_path: Path,
    *,
    xinclude: bool = True,
    idcheck: bool = True,
) -> CompletedProcess:
    """Validate an XML file against a RELAX NG schema using jing.

    If `xinclude` is True (the default), this function resolves XIncludes by
    running `xmllint --xinclude` and piping its output to `jing`. This is
    more robust for complex XInclude statements, including those with XPointer.

    :param xmlfile: The path to the XML file to validate.
    :param rng_schema_path: The path to the RELAX NG schema file.
        It supports both RNC and RNG formats.
    :param xinclude: If True, resolve XIncludes with `xmllint` before validation.
    :param idcheck: If True, perform ID uniqueness checks.
    :return: A tuple containing a boolean success status and any output message.
    """
    jing_cmd = ["jing"]
    if not idcheck:
        # The logic is that "-i" disables ID uniqueness checks in jing
        # By default jing performs ID/IDREF/IDREFS checks
        jing_cmd.append("-i")
    if rng_schema_path.suffix == ".rnc":
        jing_cmd.append("-c")
    jing_cmd.append(str(rng_schema_path))

    # Use XInclude resolution through Xerces when xinclude is True
    jing_environment = {
        # openSUSE
        "ADDITIONAL_FLAGS": XINCLUDE_PROP,
        # Fedora
        "JAVA_OPTS": XINCLUDE_PROP,
        # Debian/Ubuntu
        "JAVA_ARGS": XINCLUDE_PROP,
    }

    try:
        jing_cmd.append(str(xmlfile))
        if xinclude:
            return await run_command(jing_cmd, env=jing_environment)
        return await run_command(jing_cmd)

    except FileNotFoundError as e:
        tool = e.filename or "xmllint/jing"
        return CompletedProcess(
            args=[tool],
            returncode=1,
            # env=jing_environment,
            stdout="",
            stderr=f"{tool} command not found. Please install it to run validation.",
        )


async def run_python_checks(
    tree: etree._ElementTree,
) -> list[tuple[str, CheckResult]]:
    """Run all registered Python-based checks against a parsed XML tree.

    :param tree: The parsed XML element tree.
    :return: A list of tuples containing check names and their results.
    """
    check_results = []
    for check in registry.registry:
        try:
            result = await asyncio.to_thread(check, tree)
            check_results.append((check.__name__, result))

        except Exception as e:
            error_result = CheckResult(success=False, messages=[f"error: {e}"])
            check_results.append((check.__name__, error_result))
    return check_results


@dataclass
class ValidationResult:
    """Normalized result of RNG validation.

    :ivar success: True when validation passed.
    :ivar exit_code: Exit code to return when validation fails (0 for success).
    :ivar message: Optional human-readable message describing the failure.
    """

    success: bool
    exit_code: int
    message: str = ""


async def run_validation(filepath: Path | str, schema_path: Path) -> ValidationResult:
    """Run RNG validation using the selected method and normalize result.

    :param filepath: Path to the XML file to validate.
    :param schema_path: Path to the RNG schema.
    :returns: A :class:`ValidationResult` describing the outcome.
    """
    path_obj = Path(filepath)

    jing_result = await validate_rng(path_obj, schema_path, idcheck=True)
    if jing_result.returncode != 0:
        output = (jing_result.stdout or "") + (jing_result.stderr or "")
        return ValidationResult(False, 10, output.strip())
    return ValidationResult(True, 0, "")


async def parse_portal_config(filepath: Path | str) -> etree._ElementTree:
    """Parse XML file using lxml in a background thread.

    Exceptions from :func:`lxml.etree.parse` (for example
    :class:`lxml.etree.XMLSyntaxError`) are propagated to the caller.

    :param filepath: Path to the XML file to parse.
    :returns: Parsed :class:`lxml.etree._ElementTree`.
    """
    return await asyncio.to_thread(parse_xml_with_xinclude_base, filepath)


async def run_checks_and_display(
    tree: etree._ElementTree,
    context: DocBuildContext,
) -> bool:
    """Execute registered Python checks and print formatted results.

    :param tree: Parsed XML tree to check.
    :param context: :class:`DocBuildContext` used to read verbosity.
    :returns: True when all checks succeeded (or when no checks are registered).
    """
    check_results = await run_python_checks(tree)

    summary_line: str | None = None
    if check_results:
        check_count = len(check_results)
        check_label = "check" if check_count == 1 else "checks"
        stage2_prefix = (
            f"[bold]Stage 2 (Python checks, {check_count} {check_label} found):[/]"
        )
        fails = [result for _, result in check_results if not result.success]
        status = "[green]success[/]" if not fails else "[red]failed[/]"
        if context.verbose > 1:
            dots = "".join(
                "[green].[/green]" if result.success else "[red]F[/red]"
                for _, result in check_results
            )
            summary_line = f"{stage2_prefix} {dots} => {status}"
        elif context.verbose >= 1 or fails:
            # Always show Stage 2 status when checks fail, even in quiet mode.
            summary_line = f"{stage2_prefix} {status}"

    if check_results:
        display_results(check_results, summary_line=summary_line, tree=tree)
    return all(result.success for _, result in check_results)


async def cache_resolved_portal_config(
    context: DocBuildContext,
    tree: etree._ElementTree,
    main_portal_config: Path,
) -> Path | None:
    """Write the resolved portal XML to cache when a cache directory is configured.

    :param context: The active DocBuild context.
    :param tree: Parsed portal XML tree, potentially with resolved XIncludes.
    :param main_portal_config: Path of the main portal XML configuration file.
    :returns: The cached XML path when written, otherwise ``None``.
    """
    envconfig = getattr(context, "envconfig", None)
    paths = getattr(envconfig, "paths", None)
    base_server_cache_dir = getattr(paths, "base_server_cache_dir", None)
    if not base_server_cache_dir:
        return None

    cached_xml_path = Path(base_server_cache_dir) / f"{main_portal_config.stem}.resolved.xml"
    cached_xml_path.parent.mkdir(parents=True, exist_ok=True)
    await asyncio.to_thread(
        tree.write,
        str(cached_xml_path),
        encoding="utf-8",
        xml_declaration=True,
        pretty_print=True,
    )
    return cached_xml_path


async def process(
    context: DocBuildContext,
    main_portal_config: Path,
    portal_schema: Path,
) -> int:
    """Asynchronous function to process validation.

    :param context: The DocBuildContext containing environment configuration.
    :param main_portal_config: Path to the main Portal XML configuration file.
    :param portal_schema: Path to the Portal RELAX NG schema file.
    :raises ValueError: If no envconfig is found.
    :return: 0 if validation passed, 1 if any failures occurred.
    """
    log.debug("Starting validation process for Portal XML config %s", main_portal_config)
    console_out.print(
        "[bold]Validating[/]\n"
        f" - Portal XML config: [cyan]{main_portal_config}[/cyan]\n"
        f" - Portal schema:     [cyan]{portal_schema}[/cyan]"
    )

    validation_result = await run_validation(main_portal_config, portal_schema)
    if not validation_result.success:
        console_err.print("")
        console_err.print("[bold]Stage 1 (RNG schema via jing):[/] [red]failed[/red]")
        console_err.print("[bold red]ERROR:[/][red] RNG validation failed[/]")
        for idx, line in enumerate(validation_result.message.splitlines(), start=1):
            console_err.print(f"{idx:3d}: {line}")
        console_err.print("[bold]Stage 2 (Python checks):[/] [yellow]skipped[/yellow]")
        return validation_result.exit_code

    console_out.print("")
    console_out.print("[bold]Stage 1 (RNG schema via jing):[/] [green]success[/green]")

    # Parse after RNG succeeds so syntax and file errors map to process-specific
    # exit codes expected by callers and tests.
    try:
        tree: etree._ElementTree = await parse_portal_config(main_portal_config)

    except etree.XMLSyntaxError as err:
        console_err.print("[bold]Stage 2 (Python checks):[/] [yellow]skipped[/yellow]")
        console_err.print("XML Syntax Error => [red]failed[/red]")
        console_err.print(f"  [bold red]Error:[/] {err}")
        return 200

    #except Exception as err:
    #    console_err.print("[bold]Stage 2 (Python checks):[/] [yellow]skipped[/yellow]")
    #    console_err.print(f"  [bold red]Error:[/] {err}")
    #    return 200

    # Run custom Python checks only after RNG validation and XML parsing succeeded.
    checks_passed = await run_checks_and_display(tree, context)

    if context.verbose > 0:  # pragma: no cover
        status = "successfully validated" if checks_passed else "failed validation"
        color = "green" if checks_passed else "red"
        console_out.print(f"Result: [{color}]Portal XML {status}[/{color}]")

    if checks_passed:
        console_out.print("[green]Portal XML validation successful.[/green]")

    return 0 if checks_passed else 1
