"""Defines the handling of metadata extraction from deliverables."""

# Based on timestamps, the bottleneck is DAPS itself, not asyncio.
#
#
# Actionable ideas
# 1. Global concurrency cap for DAPS jobs
# Replace the nested parallelism with a single global semaphore or a flattened
# queue of (deliverable, lang) jobs so max_workers truly limits total DAPS
# processes. Right now, max_workers can be multiplied by translations per deliverable.
#
# 2. Log actual parallelism
# Add a log line showing how many DAPS tasks are running concurrently (just
# for one run). If you see 30–60 concurrent DAPS processes, that would explain
# the slowdown.
#

import asyncio
from collections.abc import Iterator, Mapping, Sequence
from contextlib import AsyncExitStack
import json
import logging
import os
from pathlib import Path
import shlex
import tempfile
import time

from lxml import etree
from rich.console import Console
from rich.progress import Progress, TaskID, TextColumn, TimeElapsedColumn
from rich.text import Text

from ...constants import DEFAULT_DELIVERABLES
from ...models.deliverable import Deliverable
from ...models.deliverable.paths import DeliverablePaths
from ...models.deliverable.translation import TranslationInfo
from ...models.doctype import Doctype
from ...models.language import LanguageCode
from ...models.manifest import (
    Archive,
    Category,
    Description,
    Document,
    DocumentFormat,
    Manifest,
)
from ...utils.concurrency import TaskFailedError, run_parallel
from ...utils.contextmgr import PersistentOnErrorTemporaryDirectory
from ...utils.doc import SafeDict
from ...utils.git import ManagedGitRepo
from ...utils.shell import run_command
from ..cmd_portal.process import parse_portal_config
from ..context import DocBuildContext

# Set up rich consoles for output
stdout = Console()
console_err = Console(stderr=True, style="red")

# Set up logging
log = logging.getLogger(__name__)


def marker_for_status(status: str, spinner_char: str) -> tuple[str, str]:
    """Return marker character and style for a status."""
    if status == "OK":
        return ".", "green"
    if status == "FAILED":
        return "F", "red"
    return spinner_char, "yellow"


def build_markers(
    deliverables: Sequence[Deliverable],
    status_map: dict[str, str],
    spinner_char: str,
) -> Text:
    """Build the status marker line for the progress display."""
    markers = Text("  ")
    for index, deliverable in enumerate(deliverables):
        status = status_map.get(deliverable.full_id, "FAILED")
        marker, style = marker_for_status(status, spinner_char)
        if index:
            markers.append(" ")
        markers.append(marker, style=style)
    return markers


def finalize_status_map(status_map: dict[str, str]) -> None:
    """Normalize any pending status to failed."""
    for deliverable_id, status in status_map.items():
        if status == "PENDING":
            status_map[deliverable_id] = "FAILED"


def report_failed_deliverables(
    deliverables: Sequence[Deliverable],
    status_map: dict[str, str],
) -> None:
    """Print a summary of failed deliverables."""
    failed_deliverables = [
        deliverable
        for deliverable in deliverables
        if status_map.get(deliverable.full_id) == "FAILED"
    ]
    if not failed_deliverables:
        return

    stdout.print("Failed deliverables:")
    for deliverable in failed_deliverables:
        lang = str(deliverable.xml.lang)
        dcfile = deliverable.xml.dcfile or deliverable.xml.id
        identifier = (
            f"{deliverable.xml.productid}/{deliverable.xml.docsetid}/"
            f"{lang}:{dcfile}"
        )
        stdout.print(f"  - {identifier}")


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
    relpath = (
        f"{lang_value}/{deliverable.xml.productid}/{deliverable.xml.docsetid}"
    )
    return meta_cache_dir / relpath / deliverable.xml.dcfile


def _write_metadata_cache_file(output_metadata: Path, content: str) -> None:
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
        await asyncio.to_thread(_write_metadata_cache_file, output_metadata, content)
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


def _read_metadata_cache_file(path: Path) -> str | None:
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
        file_text = await asyncio.to_thread(_read_metadata_cache_file, output_metadata)
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


def build_document_for_deliverable(
    deliverable: Deliverable,
    metadata_payload: dict[str, object],
    *,
    lang: str | LanguageCode | None = None,
) -> Document:
    """Build a Document from a deliverable and metadata payload.

    :param deliverable: Deliverable to process.
    :param metadata_payload: Parsed metadata payload.
    :param lang: Optional language override for translated deliverables.
    :return: Normalized Document instance.
    :raises ValueError: When no document payload is available.
    """
    lang_value = lang if lang is not None else deliverable.xml.lang
    lang_code = (
        lang_value
        if isinstance(lang_value, LanguageCode)
        else LanguageCode(language=str(lang_value))
    )
    lang_text = str(lang_code)
    dcfile = deliverable.xml.dcfile or ""
    document = Document.from_metadata_payload(
        metadata_payload,
        dcfile=dcfile,
        lang=lang_text,
    )
    if not document.docs:
        raise ValueError("Metadata payload missing document data.")

    rootid = document.docs[0].rootid
    document.docs[0].dcfile = dcfile
    document.docs[0].lang = lang_text
    document.docs[0].rootid = rootid
    paths = DeliverablePaths(deliverable.xml, rootid=rootid, lang=lang_code)
    fmt = deliverable.format
    doc_format = DocumentFormat(html=paths.html_path)
    if fmt.get("pdf"):
        doc_format.pdf = paths.pdf_path
    if fmt.get("single-html"):
        doc_format.single_html = paths.singlehtml_path

    document.docs[0].format = doc_format
    return document


def write_manifest_json(json_path: Path, manifest: Manifest) -> None:
    """Write a manifest JSON file atomically.

    :param json_path: Destination JSON file path.
    :param manifest: Manifest data to serialize.
    """
    json_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path: Path | None = None
    payload = manifest.model_dump(by_alias=True)

    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=str(json_path.parent),
            delete=False,
            prefix=f".{json_path.stem}.",
            suffix=".tmp",
        ) as tmp_file:
            tmp_path = Path(tmp_file.name)
            json.dump(payload, tmp_file, indent=2, ensure_ascii=False)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())

        if json_path.exists():
            tmp_path.chmod(json_path.stat().st_mode)

        tmp_path.replace(json_path)

        dir_fd = os.open(str(json_path.parent), os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
        tmp_path = None

    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink()


def build_document_from_deliverable(deliverable: Deliverable) -> Document | None:
    """Return the document stored for the deliverable."""
    document = getattr(deliverable, "document", None)
    if isinstance(document, Document):
        return document
    return None


def merge_document_docs(target: Document, source: Document) -> None:
    """Merge docs from another document into the target document."""
    existing_langs = {doc.lang for doc in target.docs if doc.lang}
    for doc in source.docs:
        if doc.lang and doc.lang in existing_langs:
            continue
        target.docs.append(doc)
        if doc.lang:
            existing_langs.add(doc.lang)


def compile_manifest(
    product: str,
    docset: str,
    deliverables: Sequence[Deliverable],
) -> Manifest | None:
    """Compile a manifest for a product/docset from deliverables.

    :param product: Product identifier.
    :param docset: Docset identifier.
    :param deliverables: Deliverables with parsed metadata.
    :return: Manifest instance or None when no data is available.
    """
    if not deliverables:
        return None

    representative = deliverables[0]
    Category.reset_rank()
    descriptions = list(Description.from_xml_node(representative))
    categories = list(Category.from_xml_node(representative))

    name_node = representative.xml.product_node.find("name")
    acronym_node = representative.xml.product_node.find("acronym")
    productname = (
        name_node.text
        if name_node is not None and name_node.text
        else product
    )
    acronym = (
        acronym_node.text
        if acronym_node is not None and acronym_node.text
        else product
    )
    lifecycle = representative.xml.docset_node.attrib.get("lifecycle") or ""

    documents_by_key: dict[str, Document] = {}
    archives: list[Archive] = []
    for deliverable in deliverables:
        document = build_document_from_deliverable(deliverable)
        if document is None:
            continue

        doc_key = ""
        if document.docs:
            doc_key = document.docs[0].dcfile or ""
        if not doc_key:
            doc_key = deliverable.xml.dcfile or deliverable.full_id
        if doc_key in documents_by_key:
            merge_document_docs(documents_by_key[doc_key], document)
        else:
            documents_by_key[doc_key] = document
        rootid = document.docs[0].rootid if document.docs else ""
        paths = DeliverablePaths(deliverable.xml, rootid=rootid)
        archives.append(
            Archive(
                lang=deliverable.xml.lang,
                default=deliverable.lang_is_default,
                zip=paths.zip_path,
            )
        )

    if not documents_by_key:
        return None

    documents = list(documents_by_key.values())

    payload = {
        "productname": productname,
        "acronym": acronym,
        "version": docset,
        "lifecycle": lifecycle,
        "hide-productname": False,
        "descriptions": descriptions,
        "categories": categories,
        "documents": documents,
        "archives": archives,
    }
    return Manifest.model_validate(payload)


async def run_metadata_progress(
    context: DocBuildContext,
    deliverables: Sequence[Deliverable],
    *,
    meta_cache_dir: Path,
    limit: int,
    description: str,
    worktrees: dict[tuple[str, str], Path],
) -> dict[str, str]:
    """Run metadata collection with a live progress display.

    :param context: The DocBuild context with environment configuration.
    :param deliverables: Deliverables to process.
    :param meta_cache_dir: Base directory for metadata cache output.
    :param limit: Maximum number of concurrent operations.
    :param description: Progress description label.
    :param worktrees: Dictionary of shared worktrees keyed by (repo_url, branch).
    :return: Status map keyed by deliverable ID.
    """
    status_map: dict[str, str] = {
        deliverable.full_id: "PENDING" for deliverable in deliverables
    }
    spinner_chars = ["|", "/", "-", "\\"]
    spinner_index = 0

    def update_progress(progress: Progress, task_id: TaskID) -> None:
        nonlocal spinner_index
        spinner_index += 1
        completed = sum(status != "PENDING" for status in status_map.values())
        success_count = sum(status == "OK" for status in status_map.values())
        failed_count = sum(status == "FAILED" for status in status_map.values())
        spinner_char = spinner_chars[spinner_index % len(spinner_chars)]
        summary = Text(f"{success_count}/{failed_count}/{len(deliverables)}")
        progress.update(
            task_id,
            completed=completed,
            markers=build_markers(deliverables, status_map, spinner_char),
            summary=summary,
        )

    async def collect(deliverable: Deliverable) -> tuple[bool, Deliverable]:
        return await collect_dynamic_metadata(
            context,
            deliverable,
            meta_cache_dir=meta_cache_dir,
            worktrees=worktrees,
        )

    stop_event = asyncio.Event()

    async def refresh_loop(progress: Progress, task_id: TaskID) -> None:
        while not stop_event.is_set():
            update_progress(progress, task_id)
            await asyncio.sleep(0.2)

    with Progress(
        TextColumn("{task.description}"),
        TextColumn("{task.fields[markers]}"),
        TimeElapsedColumn(),
        TextColumn("{task.fields[summary]}"),
        console=stdout,
        transient=False,
    ) as progress:
        task_id: TaskID = progress.add_task(
            description,
            total=len(deliverables),
            markers=build_markers(deliverables, status_map, spinner_chars[0]),
            summary=Text(f"0/0/{len(deliverables)}"),
        )
        refresher = asyncio.create_task(refresh_loop(progress, task_id))
        async for result in run_parallel(deliverables, collect, limit=limit):
            if isinstance(result, TaskFailedError):
                log.error(
                    "Metadata task failed for %s: %s",
                    result.item.full_id,
                    result.original_exception,
                )
                status_map[result.item.full_id] = "FAILED"
                update_progress(progress, task_id)
                continue

            success, deliverable = result
            if success:
                status_map[deliverable.full_id] = "OK"
            else:
                status_map[deliverable.full_id] = "FAILED"
                log.error("Metadata generation failed for %s", deliverable.full_id)
            update_progress(progress, task_id)

        finalize_status_map(status_map)
        update_progress(progress, task_id)
        stop_event.set()
        await asyncio.gather(refresher)

    return status_map


def get_deliverables_for_doctype(
    root: etree._ElementTree,
    doctype: Doctype,
) -> Iterator[Deliverable]:
    """Return DC deliverables that match a single doctype.

    :param root: Parsed portal XML tree with stitched configuration.
    :param doctype: Doctype selector provided by the user.
    :return: Iterator of DC deliverables matching the selector.
    """
    # Use the doctype XPath to locate locale nodes, then filter DC deliverables.
    languages = root.getroot().xpath(doctype.xpath())
    for language in languages:
        for node in language.findall("deliverable"):
            deliverable = Deliverable(node)
            if deliverable.xml.is_dc:
                yield deliverable


def iter_doctype_groups(
    root: etree._ElementTree,
    doctypes: Sequence[Doctype],
) -> Iterator[tuple[str, str, list[Deliverable]]]:
    """Yield product/docset groups for each doctype.

    :param root: Parsed portal XML tree with stitched configuration.
    :param doctypes: Doctype selectors provided by the user.
    :yield: Tuples of (product, docset, deliverables).
    """
    for doctype in doctypes:
        deliverables = get_deliverables_for_doctype(root, doctype)
        grouped: dict[tuple[str, str], list[Deliverable]] = {}
        for deliverable in deliverables:
            product = deliverable.xml.productid
            docset = deliverable.xml.docsetid
            grouped.setdefault((product, docset), []).append(deliverable)

        for (product, docset), grouped_deliverables in grouped.items():
            yield product, docset, grouped_deliverables


async def update_repositories_for_deliverables(
    repo_dir: Path,
    repos: set[str],
    updated_repos: set[str],
    *,
    limit: int,
) -> list[str]:
    """Update bare repositories for deliverables, once per repo URL.

    :param repo_dir: Root directory for bare repositories.
    :param repos: Repository URLs derived from deliverables.
    :param updated_repos: Set of repo URLs already updated in this run.
    :param limit: Maximum number of concurrent repo updates.
    :return: List of repository slugs successfully updated in this call.
    """
    repos_to_update: list[ManagedGitRepo] = []
    for repo_url in repos:
        if repo_url in updated_repos:
            continue
        updated_repos.add(repo_url)
        repos_to_update.append(ManagedGitRepo(repo_url, repo_dir))

    if not repos_to_update:
        return []

    async def clone(repo: ManagedGitRepo) -> tuple[ManagedGitRepo, bool]:
        return repo, await repo.clone_bare()

    updated_slugs: list[str] = []
    async for result in run_parallel(repos_to_update, clone, limit=limit):
        if isinstance(result, TaskFailedError):
            log.error(
                "Failed to update repository %s: %s",
                result.item.slug,
                result.original_exception,
            )
            continue

        repo, success = result
        if not success:
            log.error("Failed to update repository %s", repo.slug)
            continue

        updated_slugs.append(repo.slug)

    return updated_slugs


async def collect_dynamic_metadata(
    context: DocBuildContext,
    deliverable: Deliverable,
    *,
    meta_cache_dir: Path,
    worktrees: dict[tuple[str, str], Path],
) -> tuple[bool, Deliverable]:
    """Run DAPS metadata for a deliverable and store the output.

    :param context: The DocBuild context with environment configuration.
    :param deliverable: Deliverable to process.
    :param meta_cache_dir: Base directory for metadata cache output.
    :param worktrees: Dictionary of shared worktrees keyed by (repo_url, branch).
    :return: Tuple of success flag and deliverable.
    """
    env = context.envconfig
    assert env is not None

    dcfile = deliverable.xml.dcfile
    if dcfile is None and deliverable.xml.is_dc:
        log.error("Deliverable missing DC file: %s", deliverable.full_id)
        return False, deliverable

    #if not deliverable.git:
    #    log.error("Deliverable missing git remote: %s", deliverable.full_id)
    #    return False, deliverable

    async def collect_for_language(
        lang: LanguageCode,
        branch: str,
        subdir: str,
    ) -> tuple[Document | None, Path | None, bool]:
        lang_label = str(lang)
        try:
            output_metadata = build_metadata_output_path(
                deliverable,
                meta_cache_dir,
                lang=lang,
            )
        except ValueError as exc:
            log.error(
                "Failed to build metadata path for %s (%s): %s",
                deliverable.full_id,
                lang_label,
                exc,
            )
            return None, None, False

        try:
            worktree_dir = worktrees.get((deliverable.git.url, branch))
            if not worktree_dir:
                log.error("Worktree not found for %s branch %s", deliverable.git.url, branch)
                return None, output_metadata, False

            dcfile_path = worktree_dir / subdir / dcfile
            await asyncio.to_thread(output_metadata.parent.mkdir, parents=True, exist_ok=True)
            builddir = worktree_dir.joinpath(
                ".build",
                f"{deliverable.xml.productid}-{deliverable.xml.docsetid}-{lang_label}",
            )
            await asyncio.to_thread(builddir.mkdir, parents=True, exist_ok=True)

            async with PersistentOnErrorTemporaryDirectory(
                dir=str(builddir),
            ) as builddir:
                await asyncio.to_thread(builddir.mkdir, parents=True, exist_ok=True)

                command = render_command_template(
                    env.build.daps.meta,
                    {
                        "dcfile": str(dcfile_path),
                        "output": str(output_metadata),
                        "builddir": str(
                            builddir
                        ),
                    },
                )
                log.info("Running DAPS command (%s)", command)

                #if command and command[0] == "daps":
                #    command.insert(1, "--builddir")
                #    build_dir = Path(worktree_dir) / ".build" / f"{deliverable.xml.productid}-{deliverable.xml.docsetid}-{lang_label}"
                #    command.insert(2, str(build_dir))

                t0_daps = time.perf_counter()
                result = await run_command(command, cwd=worktree_dir)
                t_daps = time.perf_counter() - t0_daps
                log.info(
                    "DAPS metadata for %s (%s) took %.3fs => %d",
                    deliverable.full_id,
                    lang_label,
                    t_daps,
                    result.returncode,
                )

            if result.returncode != 0:
                log.error(
                    "DAPS metadata failed for %s (%s): %s",
                    deliverable.full_id,
                    lang_label,
                    result.stderr,
                )
                return None, output_metadata, False

        except Exception as exc:
            log.error(
                "Failed to collect metadata for %s (%s): %s",
                deliverable.full_id,
                lang_label,
                exc,
            )
            return None, output_metadata, False
        metadata_text = await read_metadata_text(
            result.stdout,
            output_metadata,
            deliverable,
        )
        if metadata_text is None:
            return None, output_metadata, False

        wrote_cache = await ensure_metadata_cache(
            metadata_text,
            output_metadata,
            deliverable,
        )

        metadata_payload = await parse_metadata_text(metadata_text, deliverable)
        if metadata_payload is None:
            return None, output_metadata, wrote_cache

        try:
            document = await asyncio.to_thread(
                build_document_for_deliverable,
                deliverable,
                metadata_payload,
                lang=lang,
            )
        except ValueError as exc:
            log.error(
                "Failed to build document for %s (%s): %s",
                deliverable.full_id,
                lang_label,
                exc,
            )
            return None, output_metadata, wrote_cache

        return document, output_metadata, wrote_cache

    base_lang = deliverable.xml.lang
    document, output_metadata, wrote_cache = await collect_for_language(
        base_lang,
        deliverable.branch,
        deliverable.subdir,
    )
    if document is None or output_metadata is None:
        return False, deliverable

    deliverable.document = document
    if wrote_cache:
        deliverable.metafile = str(output_metadata)

    translations = sorted(
        deliverable.translations.values(),
        key=lambda info: str(info.lang),
    )
    translation_failed = False
    if translations:
        appconfig = context.appconfig
        translation_limit = (
            appconfig.max_workers
            if appconfig and appconfig.max_workers
            else 1
        )
        translation_limit = max(
            1,
            min(translation_limit, len(translations)),
        )
        translation_jobs: list[tuple[TranslationInfo, str, str]] = []
        for info in translations:
            branch = (
                info.branch
                if info.branch is not None
                else deliverable.branch
            )
            subdir = (
                info.subdir
                if info.subdir is not None
                else deliverable.subdir
            )
            translation_jobs.append((info, branch, subdir))

        async def collect_translation(
            job: tuple[TranslationInfo, str, str],
        ) -> tuple[TranslationInfo, Document | None]:
            info, branch, subdir = job
            translated_doc, _, _ = await collect_for_language(
                info.lang,
                branch,
                subdir,
            )
            return info, translated_doc

        async for result in run_parallel(
            translation_jobs,
            collect_translation,
            limit=translation_limit,
        ):
            if isinstance(result, TaskFailedError):
                translation_failed = True
                continue
            info, translated_doc = result
            if translated_doc is None:
                translation_failed = True
                continue
            merge_document_docs(document, translated_doc)

    if translation_failed:
        return False, deliverable
    return True, deliverable


async def process_doctype_group(
    context: DocBuildContext,
    product: str,
    docset: str,
    deliverables: Sequence[Deliverable],
    *,
    repo_dir: Path,
    updated_repos: set[str],
    meta_cache_dir: Path,
    json_cache_dir: Path,
    limit: int,
    skip_repo_update: bool,
) -> None:
    """Process one product/docset group for repo updates and metadata.

    :param context: The DocBuild context with environment configuration.
    :param product: Product identifier for display purposes.
    :param docset: Docset identifier for display purposes.
    :param deliverables: Deliverables in the product/docset group.
    :param repo_dir: Root directory for bare repositories.
    :param updated_repos: Set of repo URLs already updated in this run.
    :param meta_cache_dir: Base directory for metadata cache output.
    :param limit: Maximum number of concurrent operations.
    :param skip_repo_update: Skip repository update step when True.
    """
    if skip_repo_update:
        log.info("Skipping repository updates for %s/%s", product, docset)
    else:
        repos = {
            repo.url
            for deliverable in deliverables
            if (repo := deliverable.xml.git_remote()) is not None
        }
        await update_repositories_for_deliverables(
            repo_dir,
            repos,
            updated_repos,
            limit=limit,
        )

    env = context.envconfig
    assert env is not None
    tmp_repo_dir = Path(env.paths.tmp_repo_dir).expanduser()
    worktrees: dict[tuple[str, str], Path] = {}

    async with AsyncExitStack() as stack:
        repo_branches: set[tuple[str, str]] = set()
        for deliverable in deliverables:
            if not deliverable.git:
                continue
            repo_url = deliverable.git.url
            repo_branches.add((repo_url, deliverable.branch))
            for info in deliverable.translations.values():
                branch = info.branch if info.branch is not None else deliverable.branch
                repo_branches.add((repo_url, branch))

        worktree_jobs: list[tuple[ManagedGitRepo, str, Path]] = []
        for repo_url, branch in repo_branches:
            repo = ManagedGitRepo(repo_url, repo_dir)
            temp_dir_ctx = PersistentOnErrorTemporaryDirectory(
                dir=str(tmp_repo_dir),
                prefix=f"shared-wt-{repo.slug}",
            )
            worktree_dir = await stack.enter_async_context(temp_dir_ctx)
            worktree_jobs.append((repo, branch, worktree_dir))

        async def create_shared_worktree(
            job: tuple[ManagedGitRepo, str, Path],
        ) -> tuple[str, str, Path, float]:
            repo, branch, worktree_dir = job
            t0_wt = time.perf_counter()
            await repo.create_worktree(worktree_dir, branch)
            t_wt = time.perf_counter() - t0_wt
            return repo.remote_url, branch, worktree_dir, t_wt

        if worktree_jobs:
            worktree_limit = max(1, min(limit, len(worktree_jobs)))
            async for result in run_parallel(
                worktree_jobs,
                create_shared_worktree,
                limit=worktree_limit,
            ):
                if isinstance(result, TaskFailedError):
                    log.error(
                        "Failed to create shared worktree for %s: %s",
                        result.item[0].remote_url,
                        result.original_exception,
                    )
                    continue
                repo_url, branch, worktree_dir, t_wt = result
                log.info(
                    "Shared worktree creation for %s (branch %s) took %.3fs",
                    repo_url,
                    branch,
                    t_wt,
                )
                worktrees[(repo_url, branch)] = worktree_dir

        description = f"{product}/{docset} ({len(deliverables)})"
        status_map = await run_metadata_progress(
            context,
            deliverables,
            meta_cache_dir=meta_cache_dir,
            limit=limit,
            description=description,
            worktrees=worktrees,
        )

    successful = [
        deliverable
        for deliverable in deliverables
        if status_map.get(deliverable.full_id) == "OK"
    ]

    t0_manifest = time.perf_counter()
    manifest = await asyncio.to_thread(compile_manifest, product, docset, successful)
    t_manifest = time.perf_counter() - t0_manifest
    log.info("Compiling manifest for %s/%s took %.3fs", product, docset, t_manifest)

    if manifest is not None:
        output_path = json_cache_dir / product / f"{docset}.json"
        await asyncio.to_thread(write_manifest_json, output_path, manifest)

    report_failed_deliverables(deliverables, status_map)


async def process(
    context: DocBuildContext,
    doctypes: Sequence[Doctype] | None,
    *,
    exitfirst: bool = False,
    skip_repo_update: bool = False,
) -> int:
    """Asynchronous function to process metadata retrieval.

    :param context: The DocBuildContext containing environment configuration.
    :param doctypes: A sequence of Doctype objects to process.
    :param exitfirst: If True, stop processing on the first failure.
    :param skip_repo_update: If True, skip updating Git repositories before processing.
    :raises ValueError: If no envconfig is found or if paths are not
        configured correctly.
    :return: 0 if all files passed validation, 1 if any failures occurred.
    """
    env = context.envconfig
    assert env is not None
    configdir = Path(env.paths.config_dir).expanduser()
    main_portal_config = Path(env.paths.main_portal_config).expanduser()
    stdout.print(f"Config path: {configdir}")

    appconfig = context.appconfig
    limit = appconfig.max_workers if appconfig and appconfig.max_workers else 1
    log.info("Using concurrency limit: %d", limit)
    repo_dir = Path(env.paths.repo_dir).expanduser()
    updated_repos: set[str] = set()
    meta_cache_dir = Path(env.paths.meta_cache_dir).expanduser()
    json_cache_dir = Path(env.paths.json_cache_dir).expanduser()

    portalnode: etree._ElementTree = await parse_portal_config(main_portal_config)

    if not doctypes:
        doctypes = [Doctype.from_str(DEFAULT_DELIVERABLES)]

    for product, docset, deliverables in iter_doctype_groups(portalnode, doctypes):
        await process_doctype_group(
            context,
            product,
            docset,
            deliverables,
            repo_dir=repo_dir,
            updated_repos=updated_repos,
            meta_cache_dir=meta_cache_dir,
            json_cache_dir=json_cache_dir,
            limit=limit,
            skip_repo_update=skip_repo_update,
        )

    return 0
