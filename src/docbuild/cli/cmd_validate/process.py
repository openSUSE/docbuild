"""Module for processing XML validation in DocBuild."""

import asyncio
from collections.abc import Iterator
import logging
from pathlib import Path
import tempfile

from lxml import etree
from rich.console import Console

from ...config.xml.checks import CheckResult, register_check
from ...config.xml.stitch import create_stitchfile
from ...constants import XMLDATADIR
from ...utils.decorators import RegistryDecorator
from ...utils.paths import calc_max_len
from ..context import DocBuildContext

# Cast to help with type checking
registry: RegistryDecorator = register_check  # type: ignore[assignment]

# Set up logging
log = logging.getLogger(__name__)

# Set up rich consoles for output
console_out = Console()
console_err = Console(stderr=True)


# Default RELAX NG schema file for product configuration
PRODUCT_CONFIG_SCHEMA = XMLDATADIR / 'product-config-schema.rnc'


def display_results(
    shortname: str,
    check_results: list[tuple[str, CheckResult]],
    verbose: int,
    max_len: int,
) -> None:
    """Display validation results based on verbosity level using rich.

    :param shortname: Shortened name of the XML file being processed.
    :param check_results: List of tuples containing check names and their results.
    :param verbose: Verbosity level (0, 1, 2)
    :param max_len: Maximum length for formatting the output.
    """
    if verbose == 0:
        return

    symbols = []
    overall_success = True
    failed_checks = []

    for check_name, result in check_results:
        if result.success:
            symbols.append('[green].[/green]')
        else:
            symbols.append('[red]F[/red]')
            overall_success = False
            failed_checks.append((check_name, result))

    status = '[green]success[/green]' if overall_success else '[red]failed[/red]'

    if verbose == 1:
        console_out.print(f'{shortname:<{max_len}}: {status}')
    else:
        dots = ''.join(symbols)
        console_out.print(f'{shortname:<{max_len}}: {dots} => {status}')

        # Show detailed error messages if any failures
        if failed_checks and verbose > 2:
            for check_name, result in failed_checks:
                console_err.print(f'    [bold red]✗ {check_name}:[/bold red]')
                for message in result.messages:
                    console_err.print(f'      {message}')


async def run_command(
    *args: str, env: dict[str, str] | None = None
) -> tuple[int, str, str]:
    """Run an external command and capture its output.

    :param args: The command and its arguments separated as tuple elements.
    :param env: A dictionary of environment variables for the new process.
    :return: A tuple of (returncode, stdout, stderr).
    :raises FileNotFoundError: if the command is not found.
    """
    process = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    stdout, stderr = await process.communicate()

    # After .communicate() returns, the process has terminated and the
    # returncode is guaranteed to be set to an integer.
    assert process.returncode is not None

    return process.returncode, stdout.decode(), stderr.decode()


async def validate_rng(
    xmlfile: Path,
    rng_schema_path: Path = PRODUCT_CONFIG_SCHEMA,
    *,
    xinclude: bool = True,
) -> tuple[bool, str]:
    """Validate an XML file against a RELAX NG schema using jing.

    If `xinclude` is True (the default), this function resolves XIncludes by
    running `xmllint --xinclude` and piping its output to `jing`. This is
    more robust for complex XInclude statements, including those with XPointer.

    :param xmlfile: The path to the XML file to validate.
    :param rng_schema_path: The path to the RELAX NG schema file. It supports
        both RNC and RNG formats.
    :param xinclude: If True, resolve XIncludes with `xmllint` before validation.
    :return: A tuple containing a boolean success status and any output message.
    """
    jing_cmd = ['jing']
    if rng_schema_path.suffix == '.rnc':
        jing_cmd.append('-c')
    jing_cmd.append(str(rng_schema_path))

    try:
        if xinclude:
            # Use a temporary file to store the output of xmllint.
            # This is more robust than piping, especially if jing doesn't
            # correctly handle stdin (the command "jing schema.rng -" does NOT work.)
            with tempfile.NamedTemporaryFile(
                prefix='jing-validation',
                suffix='.xml',
                mode='w',
                delete=True,
                encoding='utf-8',
            ) as tmp_file:
                tmp_filepath = Path(tmp_file.name)

                # 1. Run xmllint to resolve XIncludes and save to temp file
                returncode, _, stderr = await run_command(
                    'xmllint', '--xinclude', '--output', str(tmp_filepath), str(xmlfile)
                )
                if returncode != 0:
                    return False, f'xmllint failed: {stderr.strip()}'

                # 2. Run jing on the resolved temporary file
                jing_cmd.append(str(tmp_filepath))
                returncode, stdout, stderr = await run_command(*jing_cmd)
                if returncode != 0:
                    return False, (stdout + stderr).strip()

                return True, ''
        else:
            # Validate directly with jing, no XInclude resolution.
            jing_cmd.append(str(xmlfile))
            returncode, stdout, stderr = await run_command(*jing_cmd)
            if returncode == 0:
                return True, ''
            return False, (stdout + stderr).strip()

    except FileNotFoundError as e:
        tool = e.filename or 'xmllint/jing'
        return (
            False,
            f'{tool} command not found. Please install it to run validation.',
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
            error_result = CheckResult(success=False, messages=[f'error: {e}'])
            check_results.append((check.__name__, error_result))
    return check_results


async def process_file(
    filepath: Path | str,
    context: DocBuildContext,
    max_len: int,
) -> int:
    """Process a single file: RNG validation then Python checks.

    :param filepath: The path to the XML file to process.
    :param context: The DocBuildContext.
    :param max_len: Maximum length for formatting the output.
    :param rng_schema_path: Optional path to an RNG schema for validation.
    :return: An exit code (0 for success, non-zero for failure).
    """
    # Shorten the filename to last two parts for display
    path_obj = Path(filepath)
    shortname = (
        '/'.join(path_obj.parts[-2:]) if len(path_obj.parts) >= 2 else str(filepath)
    )

    # IDEA: Should we replace jing and validate with etree.RelaxNG?

    # 1. RNG Validation
    rng_success, rng_output = await validate_rng(path_obj)
    if not rng_success:
        console_err.print(
            f'{shortname:<{max_len}}: RNG validation => [red]failed[/red]'
        )
        if rng_output:
            console_err.print(f'  [bold red]Error:[/] {rng_output}')
        return 10  # Specific error code for RNG failure

    # 2. Python-based checks
    try:
        tree = await asyncio.to_thread(etree.parse, str(filepath), parser=None)

    except etree.XMLSyntaxError as err:
        # This can happen if xmllint passes but lxml's parser is stricter.
        console_err.print(
            f'{shortname:<{max_len}}: XML Syntax Error => [red]failed[/red]'
        )
        console_err.print(f'  [bold red]Error:[/] {err}')
        return 20

    except Exception as err:
        console_err.print(f'  [bold red]Error:[/] {err}')
        return 200

    # Run all checks for this file
    check_results = await run_python_checks(tree)

    # Display results based on verbosity level
    display_results(shortname, check_results, context.verbose, max_len)

    return 0 if all(result.success for _, result in check_results) else 1


async def process(
    context: DocBuildContext,
    xmlfiles: tuple[Path | str, ...] | Iterator[Path],
) -> int:
    """Asynchronous function to process validation.

    :param context: The DocBuildContext containing environment configuration.
    :param xmlfiles: A tuple or iterator of XML file paths to validate.
    :raises ValueError: If no envconfig is found or if paths are not
        configured correctly.
    :return: 0 if all files passed validation, 1 if any failures occurred.
    """
    # Prepare the context and validate environment configuration
    if context.envconfig is None:
        raise ValueError('No envconfig found in context.')

    paths = context.envconfig.get('paths', {})
    if not isinstance(paths, dict):
        raise ValueError("'paths.config' must be a dictionary.")

    configdir = paths.get('config_dir', None)
    log.debug(f'Async Processing validation with {configdir=}...')
    log.debug(f'Registry has {len(registry.registry)} checks registered')

    # Convert iterator to tuple if needed to get total count
    if isinstance(xmlfiles, Iterator):
        xmlfiles = tuple(xmlfiles)

    if not xmlfiles:
        log.warning('No XML files found to validate.')
        return 0

    total_files = len(xmlfiles)
    max_len = calc_max_len(xmlfiles)

    # Process files concurrently but print results as they complete
    tasks = [process_file(xml, context, max_len) for xml in xmlfiles]
    results = await asyncio.gather(*tasks)

    # Filter for files that passed the initial validation
    successful_files_paths = [
        xmlfile for xmlfile, result in zip(xmlfiles, results) if result == 0
    ]

    # After validating individual files, perform a stitch validation to
    # check for cross-file issues like duplicate product IDs.
    stitch_success = True
    if successful_files_paths:
        try:
            log.info('Performing stitch-file validation...')
            await create_stitchfile(successful_files_paths)
            log.info('Stitch-file validation successful.')

        except ValueError as e:
            # Using rich for better visibility of this critical error
            console_err.print(f'[bold red]Stitch-file validation failed:[/] {e}')
            stitch_success = False

    # Calculate summary statistics
    successful_files = sum(1 for result in results if result == 0)
    failed_files = total_files - successful_files

    # Display summary
    successful_part = f'[green]{successful_files}/{total_files} files(s)[/green]'
    failed_part = f'[red]{failed_files} file(s)[/red]'
    summary_msg = f'{successful_part} successfully validated, {failed_part} failed.'

    if context.verbose > 0:
        console_out.print(f'Result: {summary_msg}')

    final_success = (failed_files == 0) and stitch_success

    return 0 if final_success else 1
