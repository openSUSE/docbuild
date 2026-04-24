"""Module for validating portal content using RNG and Python checks."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import logging
from pathlib import Path
from subprocess import CompletedProcess
import tempfile
from typing import TYPE_CHECKING, cast

from rich.console import Console

from ....config.xml.stitch import create_stitchfile
from ....constants import XMLDATADIR
from ....utils.paths import calc_max_len
from ....utils.shell import run_command

if TYPE_CHECKING:
    from rich.console import Console

    from docbuild.cli.context import DocBuildContext
    from docbuild.models.doctype import Doctype

log = logging.getLogger(__name__)
console_out = Console()
console_err = Console(stderr=True)


PRODUCT_CONFIG_SCHEMA = XMLDATADIR / "product-config-schema.rnc"


@dataclass
class ValidationResult:
    """Structured result for validation outcomes."""

    success: bool
    exit_code: int
    message: str = ""


# --- Helper Logic harvested from old process.py ---

async def validate_rng(xmlfile: Path, rng_schema_path: Path = PRODUCT_CONFIG_SCHEMA) -> CompletedProcess:
    """Validate an XML file against a RELAX NG schema using jing.

    :param xmlfile: The XML file to validate.
    :param rng_schema_path: The path to the RELAX NG schema file.
    :return: A CompletedProcess object with the result of the validation.
    """
    jing_cmd = ["jing", "-i"]
    if rng_schema_path.suffix == ".rnc":
        jing_cmd.append("-c")
    jing_cmd.append(str(rng_schema_path))

    try:
        with tempfile.NamedTemporaryFile(prefix="jing-", suffix=".xml", delete=True) as tmp_file:
            tmp_filepath = Path(tmp_file.name)
            # Resolve XIncludes
            xmllint_proc = await run_command(["xmllint", "--xinclude", "--output", str(tmp_filepath), str(xmlfile)])
            if xmllint_proc.returncode != 0:
                return CompletedProcess(args=["xmllint"], returncode=xmllint_proc.returncode, stdout="", stderr="xmllint failed")

            jing_cmd.append(str(tmp_filepath))
            return await run_command(jing_cmd)
    except Exception as e:
        return CompletedProcess(args=["jing"], returncode=1, stdout="", stderr=str(e))


async def process_file(filepath: Path, context: DocBuildContext, max_len: int) -> int:
    """Process a single file: RNG validation.

    :param filepath: The path to the XML file to validate.
    :param context: The DocBuildContext containing configuration and state.
    :param max_len: The maximum length of file paths for aligned console output.
    :return: 0 if validation passed, 1 if it failed.
    """
    shortname = "/".join(filepath.parts[-2:])
    validation_proc = await validate_rng(filepath)

    if validation_proc.returncode != 0:
        console_err.print(f"{shortname:<{max_len}}: RNG validation => [red]failed[/red]")
        return 1

    console_out.print(f"{shortname:<{max_len}}: RNG validation => [green]passed[/green]")
    return 0


async def process(context: DocBuildContext, xmlfiles: tuple[Path, ...]) -> int:
    """Coordinate the core validation tasks.

    :param context: The DocBuildContext containing configuration and state.
    :param xmlfiles: A tuple of XML file paths to validate.
    :return: 0 if all validations passed, 1 if any failed.
    """
    if not xmlfiles:
        return 0

    max_len = calc_max_len(xmlfiles)
    tasks = [process_file(xml, context, max_len) for xml in xmlfiles]
    results = await asyncio.gather(*tasks)

    # Stitching logic
    successful_paths = [path for path, res in zip(xmlfiles, results, strict=True) if res == 0]
    if successful_paths:
        try:
            await create_stitchfile(successful_paths)
            log.info("Stitch-file validation successful.")
        except Exception as e:
            console_err.print(f"[bold red]Stitch-file validation failed:[/] {e}")
            return 1

    return 0 if all(res == 0 for res in results) else 1


# --- The CLI Entry Point ---

async def validate_portal_content(ctx_obj: DocBuildContext, console: Console) -> bool:
    """Perform deep validation of portals using RNG and Python checks.

    :param ctx_obj: The DocBuildContext containing configuration and state.
    :param console: The console object for printing messages.
    :return: True if validation passed, False otherwise.
    """
    doctypes: list[Doctype] = ctx_obj.doctypes or []

    if not doctypes:
        console.print("\n⚠️ [bold yellow]Portals/Doctypes:[/bold yellow] None discovered")
        return False

    console.print(f"\n🔍 [bold]Deep Validating {len(doctypes)} Portals...[/bold]")

    xml_paths = []
    for dt in doctypes:
        path_val = getattr(dt, "path", None)
        if path_val:
            xml_paths.append(Path(cast(str, path_val)))

    if not xml_paths:
        console.print("   [red]error: No file paths found for discovered doctypes.[/red]")
        return False

    exit_code = await process(ctx_obj, tuple(xml_paths))
    return exit_code == 0
