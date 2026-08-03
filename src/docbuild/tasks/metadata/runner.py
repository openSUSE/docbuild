"""Task orchestration and main entry point for metadata processing."""

import asyncio
from collections.abc import Sequence
import logging
from pathlib import Path

from lxml import etree
from rich.console import Console

from docbuild.constants import DEFAULT_DELIVERABLES
from docbuild.models.deliverable import Deliverable
from docbuild.models.doctype import Doctype
from docbuild.tasks.portal import parse_portal_config

from .daps import process_deliverable
from .deliverables import get_deliverable_from_doctype
from .manifest import store_productdocset_json
from .repos import update_repositories

log = logging.getLogger(__name__)
stdout = Console()
console_err = Console(stderr=True, style="red")


async def run_tasks_fail_fast(tasks: list[asyncio.Task]) -> list[Deliverable]:
    """Execute tasks and stop immediately on the first failure.

    :param tasks: List of asyncio Tasks wrapping ``process_deliverable`` coroutines.
    :return: A list containing the first failed Deliverable, or an empty list.
    """
    failed: list[Deliverable] = []
    for task in asyncio.as_completed(tasks):
        try:
            success, deliverable = await task
            if not success:
                failed.append(deliverable)
                for t in tasks:
                    if not t.done():
                        t.cancel()
                break
        except Exception as e:
            log.error("Task failed unexpectedly: %s", e)
            for t in tasks:
                if not t.done():
                    t.cancel()
            break
    return failed


async def run_tasks_collect_all(
    tasks: list[asyncio.Task], deliverables: list[Deliverable]
) -> list[Deliverable]:
    """Execute all tasks and collect every failure encountered.

    :param tasks: List of asyncio Tasks wrapping ``process_deliverable`` coroutines.
    :param deliverables: The matching list of Deliverables (same order as tasks).
    :return: A list of all Deliverables that failed.
    """
    failed: list[Deliverable] = []
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for deliverable, result in zip(deliverables, results, strict=False):
        if isinstance(result, tuple):
            success, res_deliverable = result
            if not success:
                failed.append(res_deliverable)
        elif isinstance(result, Exception):
            log.error("Error in task for %s: %s", deliverable.full_id, result)
            failed.append(deliverable)
    return failed


async def run_metadata_tasks(
    tasks: list[asyncio.Task], deliverables: list[Deliverable], exitfirst: bool
) -> list[Deliverable]:
    """Execute metadata tasks using either fail-fast or collect-all strategy.

    :param tasks: List of asyncio Tasks to execute.
    :param deliverables: The matching Deliverables list.
    :param exitfirst: When ``True``, stop on the first failure.
    :return: A list of failed Deliverables.
    """
    if exitfirst:
        return await run_tasks_fail_fast(tasks)
    return await run_tasks_collect_all(tasks, deliverables)


async def process_doctype(
    root: etree._ElementTree,
    doctype: Doctype,
    repo_dir: Path,
    tmp_repo_dir: Path,
    meta_cache_dir: Path,
    dapsmetatmpl: str,
    max_workers: int,
    *,
    exitfirst: bool = False,
    skip_repo_update: bool = False,
) -> list[Deliverable]:
    """Process the doctypes and create metadata files.

    :param root: The stitched XML node containing configuration.
    :param doctype: The Doctype object to process.
    :param repo_dir: Path to the repositories directory.
    :param tmp_repo_dir: Path to the temporary repositories directory.
    :param meta_cache_dir: Path to the metadata cache output directory.
    :param dapsmetatmpl: Template string for the DAPS command.
    :param max_workers: Maximum number of concurrent workers allowed.
    :param exitfirst: If True, stop processing on the first failure.
    :param skip_repo_update: If True, do not fetch updates for the git repositories.
    :return: A list of failed Deliverables.
    """
    deliverables: list[Deliverable] = await asyncio.to_thread(
        get_deliverable_from_doctype, root, doctype
    )

    if skip_repo_update:
        log.info("Skipping repository %s updates as requested.", repo_dir)
    else:
        await update_repositories(deliverables, repo_dir)

    worker_limit = max(1, min(max_workers, len(deliverables)))
    semaphore = asyncio.Semaphore(worker_limit)

    async def process_deliverable_limited(
        deliverable: Deliverable,
    ) -> tuple[bool, Deliverable]:
        async with semaphore:
            return await process_deliverable(
                deliverable,
                repo_dir,
                tmp_repo_dir,
                meta_cache_dir,
                dapstmpl=dapsmetatmpl,
            )

    tasks = [
        asyncio.create_task(
            process_deliverable_limited(d),
            name=f"process_deliverable_{d.full_id}",
        )
        for d in deliverables
    ]

    return await run_metadata_tasks(tasks, deliverables, exitfirst)


async def process(
    main_portal_config: Path,
    tmp_metadata_dir: Path,
    repo_dir: Path,
    tmp_repo_dir: Path,
    meta_cache_dir: Path,
    json_cache_dir: Path,
    dapsmetatmpl: str,
    max_workers: int,
    doctypes: Sequence[Doctype] | None,
    *,
    exitfirst: bool = False,
    skip_repo_update: bool = False,
) -> int:
    """Asynchronous entry point for metadata retrieval.

    :param main_portal_config: Path to the main portal XML configuration.
    :param tmp_metadata_dir: Path to the temporary metadata directory.
    :param repo_dir: Path to the repositories directory.
    :param tmp_repo_dir: Path to the temporary repositories directory.
    :param meta_cache_dir: Path to the metadata cache output directory.
    :param json_cache_dir: Path to the JSON cache output directory.
    :param dapsmetatmpl: Template string for the DAPS command.
    :param max_workers: Maximum number of concurrent workers allowed.
    :param doctypes: A sequence of Doctype objects to process.
    :param exitfirst: If True, stop processing on the first failure.
    :param skip_repo_update: If True, skip updating Git repositories before processing.
    :return: 0 if all files passed validation, 1 if any failures occurred.
    """
    stitchnode: etree._ElementTree = await parse_portal_config(main_portal_config)

    tmp_metadata_dir.mkdir(parents=True, exist_ok=True)

    stitchfilename = tmp_metadata_dir / "stitched-metadata.xml"
    stitchfilename.write_text(
        etree.tostring(
            stitchnode,
            pretty_print=True,
            encoding="unicode",
        )
    )

    log.info("Stitched metadata XML written to %s", str(stitchfilename))

    if not doctypes:
        doctypes = [Doctype.from_str(DEFAULT_DELIVERABLES, default_lang="*")]

    tasks = [
        process_doctype(
            stitchnode,
            dt,
            repo_dir,
            tmp_repo_dir,
            meta_cache_dir,
            dapsmetatmpl,
            max_workers,
            exitfirst=exitfirst,
            skip_repo_update=skip_repo_update,
        )
        for dt in doctypes
    ]
    results_per_doctype = await asyncio.gather(*tasks)

    all_failed_deliverables = [
        d for failed_list in results_per_doctype for d in failed_list
    ]

    store_productdocset_json(doctypes, stitchnode, meta_cache_dir, json_cache_dir)

    if all_failed_deliverables:
        console_err.print(f"Found {len(all_failed_deliverables)} failed deliverables:")
        for d in all_failed_deliverables:
            console_err.print(f"- {d.full_id}")
        return 1

    return 0
