"""Metadata cache and command rendering helpers for DAPS collection."""

import asyncio
from collections.abc import Mapping
import json
import logging
from pathlib import Path
import shlex

from ...models.deliverable import Deliverable
from ...models.language import LanguageCode
from ...utils.doc import SafeDict

log = logging.getLogger(__name__)


def render_command_template(
    template: str,
    values: Mapping[str, str],
) -> list[str]:
    """Render and split a command template.

    :param template: Command template to split.
    :param values: Placeholder values for ``str.format_map``.
    :return: Command tokens suitable for subprocess execution.
    :raises ValueError: When the template is empty.
    """
    rendered = template.format_map(SafeDict(values))
    tokens = shlex.split(rendered)
    if not tokens:
        raise ValueError("Command template is empty.")
    return tokens


def build_metadata_output_path(
    deliverable: Deliverable,
    meta_cache_dir: Path,
    *,
    lang: str | LanguageCode | None = None,
) -> Path:
    """Build the metadata cache path for a deliverable.

    :param deliverable: Deliverable to process.
    :param meta_cache_dir: Base directory for metadata cache output.
    :param lang: Optional language override for translated deliverables.
    :return: Path to the metadata cache file.
    :raises ValueError: When the deliverable is missing a DC file.
    """
    if deliverable.xml.dcfile is None:
        raise ValueError("Deliverable is missing a DC file.")
    lang_value = lang if lang is not None else deliverable.xml.lang
    relpath = f"{lang_value}/{deliverable.xml.productid}/{deliverable.xml.docsetid}"
    return meta_cache_dir / relpath / deliverable.xml.dcfile


def write_metadata_cache_file(output_metadata: Path, content: str) -> None:
    """Write metadata cache file synchronously."""
    output_metadata.parent.mkdir(parents=True, exist_ok=True)
    output_metadata.write_text(content, encoding="utf-8")


async def write_metadata_cache(
    output_metadata: Path,
    content: str,
    deliverable: Deliverable,
) -> bool:
    """Write metadata JSON to cache if possible.

    :param output_metadata: Destination path for cached metadata.
    :param content: Metadata JSON content.
    :param deliverable: Deliverable used for logging context.
    :return: True when the cache file was written.
    """
    try:
        await asyncio.to_thread(write_metadata_cache_file, output_metadata, content)
    except OSError as exc:
        log.warning(
            "Failed to write metadata cache for %s: %s",
            deliverable.full_id,
            exc,
        )
        return False
    return True


def compile_metadata(text: str) -> dict[str, object]:
    """Parse metadata JSON text output.

    :param text: JSON metadata output.
    :return: Parsed metadata payload.
    :raises ValueError: When the metadata is not a JSON object.
    """
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("Metadata JSON must be an object.")
    return payload


def read_metadata_cache_file(path: Path) -> str | None:
    """Read metadata cache file synchronously."""
    if path.exists():
        return path.read_text(encoding="utf-8")
    return None


async def read_metadata_text(
    stdout: str,
    output_metadata: Path,
    deliverable: Deliverable,
) -> str | None:
    """Return metadata text from stdout or cached output.

    :param stdout: Metadata stdout text.
    :param output_metadata: Expected metadata cache path.
    :param deliverable: Deliverable used for logging context.
    :return: Metadata text if available.
    """
    try:
        file_text = await asyncio.to_thread(read_metadata_cache_file, output_metadata)
    except OSError as exc:
        log.error(
            "Failed to read metadata cache for %s: %s",
            deliverable.full_id,
            exc,
        )
        return None

    if file_text and file_text.strip():
        return file_text

    if stdout.strip():
        return stdout

    log.error("DAPS metadata produced no output for %s", deliverable.full_id)
    return None


async def ensure_metadata_cache(
    metadata_text: str,
    output_metadata: Path,
    deliverable: Deliverable,
) -> bool:
    """Ensure metadata is cached on disk.

    :param metadata_text: Metadata JSON text output.
    :param output_metadata: Destination cache path.
    :param deliverable: Deliverable used for logging context.
    :return: True when a cache file exists or was written.
    """
    if await asyncio.to_thread(output_metadata.exists):
        return True
    return await write_metadata_cache(output_metadata, metadata_text, deliverable)


async def parse_metadata_text(
    metadata_text: str,
    deliverable: Deliverable,
) -> dict[str, object] | None:
    """Parse metadata JSON into a payload dictionary.

    :param metadata_text: Metadata JSON text output.
    :param deliverable: Deliverable used for logging context.
    :return: Parsed metadata payload or None on failure.
    """
    try:
        return await asyncio.to_thread(compile_metadata, metadata_text)
    except Exception as exc:
        log.error("Failed to parse metadata for %s: %s", deliverable.full_id, exc)
        return None
