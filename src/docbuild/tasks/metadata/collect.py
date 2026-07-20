"""DAPS-driven metadata collection for deliverables and translations."""

import asyncio
import logging
from pathlib import Path
import time

from ...cli.context import DocBuildContext
from ...models.deliverable import Deliverable
from ...models.deliverable.translation import TranslationInfo
from ...models.language import LanguageCode
from ...models.manifest import Document
from ...utils.concurrency import TaskFailedError, run_parallel
from ...utils.contextmgr import PersistentOnErrorTemporaryDirectory
from ...utils.shell import run_command
from .cache import (
    build_metadata_output_path,
    ensure_metadata_cache,
    parse_metadata_text,
    read_metadata_text,
    render_command_template,
)
from .manifest import build_document_for_deliverable, merge_document_docs

log = logging.getLogger(__name__)


def _translation_jobs(
    deliverable: Deliverable,
) -> list[tuple[TranslationInfo, str, str]]:
    """Build normalized translation jobs for a deliverable."""
    jobs: list[tuple[TranslationInfo, str, str]] = []
    for info in sorted(deliverable.translations.values(), key=lambda item: str(item.lang)):
        branch = info.branch if info.branch is not None else deliverable.branch
        subdir = info.subdir if info.subdir is not None else deliverable.subdir
        jobs.append((info, branch, subdir))
    return jobs


def _translation_limit(context: DocBuildContext, translation_count: int) -> int:
    """Return the bounded concurrency for translation metadata jobs."""
    appconfig = context.appconfig
    configured_limit = appconfig.max_workers if appconfig and appconfig.max_workers else 1
    return max(1, min(configured_limit, translation_count))


async def _collect_language_metadata(
    context: DocBuildContext,
    deliverable: Deliverable,
    repo_url: str,
    dcfile: str,
    *,
    meta_cache_dir: Path,
    worktrees: dict[tuple[str, str], Path],
    lang: LanguageCode,
    branch: str,
    subdir: str,
) -> tuple[Document | None, Path | None, bool]:
    """Collect metadata for one deliverable language variant."""
    env = context.envconfig
    assert env is not None

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

    worktree_dir = worktrees.get((repo_url, branch))
    if not worktree_dir:
        log.error("Worktree not found for %s branch %s", repo_url, branch)
        return None, output_metadata, False

    try:
        dcfile_path = worktree_dir / subdir / dcfile
        await asyncio.to_thread(output_metadata.parent.mkdir, parents=True, exist_ok=True)
        builddir = worktree_dir.joinpath(
            ".build",
            f"{deliverable.xml.productid}-{deliverable.xml.docsetid}-{lang_label}",
        )
        await asyncio.to_thread(builddir.mkdir, parents=True, exist_ok=True)

        async with PersistentOnErrorTemporaryDirectory(dir=str(builddir)) as tmp_builddir:
            await asyncio.to_thread(tmp_builddir.mkdir, parents=True, exist_ok=True)
            command = render_command_template(
                env.build.daps.meta,
                {
                    "dcfile": str(dcfile_path),
                    "output": str(output_metadata),
                    "builddir": str(tmp_builddir),
                },
            )
            log.info("Running DAPS command (%s)", command)

            started_at = time.perf_counter()
            result = await run_command(command, cwd=worktree_dir)
            elapsed = time.perf_counter() - started_at
            log.info(
                "DAPS metadata for %s (%s) took %.3fs => %d",
                deliverable.full_id,
                lang_label,
                elapsed,
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

    metadata_text = await read_metadata_text(result.stdout, output_metadata, deliverable)
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


async def _collect_translations(
    context: DocBuildContext,
    deliverable: Deliverable,
    document: Document,
    repo_url: str,
    dcfile: str,
    *,
    meta_cache_dir: Path,
    worktrees: dict[tuple[str, str], Path],
) -> bool:
    """Collect translation metadata and merge successful document variants."""
    translation_jobs = _translation_jobs(deliverable)
    if not translation_jobs:
        return True

    async def collect_translation(
        job: tuple[TranslationInfo, str, str],
    ) -> tuple[TranslationInfo, Document | None]:
        info, branch, subdir = job
        translated_doc, _, _ = await _collect_language_metadata(
            context,
            deliverable,
            repo_url,
            dcfile,
            meta_cache_dir=meta_cache_dir,
            worktrees=worktrees,
            lang=info.lang,
            branch=branch,
            subdir=subdir,
        )
        return info, translated_doc

    translation_failed = False
    async for result in run_parallel(
        translation_jobs,
        collect_translation,
        limit=_translation_limit(context, len(translation_jobs)),
    ):
        if isinstance(result, TaskFailedError):
            translation_failed = True
            continue

        _, translated_doc = result
        if translated_doc is None:
            translation_failed = True
            continue
        merge_document_docs(document, translated_doc)

    return not translation_failed


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
    :param worktrees: Shared worktrees keyed by repository URL and branch.
    :return: Tuple of success flag and deliverable.
    """
    repo = deliverable.git
    dcfile = deliverable.xml.dcfile
    if repo is None:
        log.error("Deliverable missing git remote: %s", deliverable.full_id)
        return False, deliverable
    if dcfile is None:
        log.error("Deliverable missing DC file: %s", deliverable.full_id)
        return False, deliverable

    document, output_metadata, wrote_cache = await _collect_language_metadata(
        context,
        deliverable,
        repo.url,
        dcfile,
        meta_cache_dir=meta_cache_dir,
        worktrees=worktrees,
        lang=deliverable.xml.lang,
        branch=deliverable.branch,
        subdir=deliverable.subdir,
    )
    if document is None or output_metadata is None:
        return False, deliverable

    deliverable.document = document
    if wrote_cache:
        deliverable.metafile = str(output_metadata)

    translations_ok = await _collect_translations(
        context,
        deliverable,
        document,
        repo.url,
        dcfile,
        meta_cache_dir=meta_cache_dir,
        worktrees=worktrees,
    )
    return translations_ok, deliverable
