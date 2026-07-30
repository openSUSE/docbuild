"""Task orchestration and main entry point for metadata processing."""

import asyncio
from collections.abc import Sequence
import logging
from pathlib import Path

from lxml import etree
from rich.console import Console

from docbuild.cli.context import DocBuildContext
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


def get_deliverable_worker_limit(
    context: DocBuildContext, deliverable_count: int
) -> int:
    """Resolve the concurrency limit for deliverable processing.

    :param context: The DocBuildContext containing application configuration.
    :param deliverable_count: Number of deliverables to process.
    :return: A worker limit between 1 and ``deliverable_count``.
    """
    if deliverable_count <= 0:
        return 1

    appconfig = context.appconfig
    if appconfig is None:
        return deliverable_count

    return max(1, min(appconfig.max_workers, deliverable_count))


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
    context: DocBuildContext,
    doctype: Doctype,
    *,
    exitfirst: bool = False,
    skip_repo_update: bool = False,
) -> list[Deliverable]:
    """Process the doctypes and create metadata files.

    :param root: The stitched XML node containing configuration.
    :param context: The DocBuildContext containing environment configuration.
    :param doctype: The Doctype object to process.
    :param exitfirst: If True, stop processing on the first failure.
    :param skip_repo_update: If True, do not fetch updates for the git repositories.
    :return: A list of failed Deliverables.
    """
    env = context.envconfig
    assert env is not None
    repo_dir: Path = env.paths.repo_dir

    deliverables: list[Deliverable] = await asyncio.to_thread(
        get_deliverable_from_doctype, root, doctype
    )

    if skip_repo_update:
        log.info("Skipping repository %s updates as requested.", repo_dir)
    else:
        await update_repositories(deliverables, repo_dir)

    dapsmetatmpl = env.build.daps.meta
    worker_limit = get_deliverable_worker_limit(context, len(deliverables))
    semaphore = asyncio.Semaphore(worker_limit)

    async def process_deliverable_limited(
        deliverable: Deliverable,
    ) -> tuple[bool, Deliverable]:
        async with semaphore:
            return await process_deliverable(
                context,
                deliverable,
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
    context: DocBuildContext,
    doctypes: Sequence[Doctype] | None,
    *,
    exitfirst: bool = False,
    skip_repo_update: bool = False,
) -> int:
    """Asynchronous entry point for metadata retrieval.

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
    stitchnode: etree._ElementTree = await parse_portal_config(main_portal_config)

    tmp_metadata_dir = env.paths.tmp.tmp_metadata_dir
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
            context,
            dt,
            exitfirst=exitfirst,
            skip_repo_update=skip_repo_update,
        )
        for dt in doctypes
    ]
    results_per_doctype = await asyncio.gather(*tasks)

    all_failed_deliverables = [
        d for failed_list in results_per_doctype for d in failed_list
    ]

    store_productdocset_json(context, doctypes, stitchnode)

    if all_failed_deliverables:
        console_err.print(f"Found {len(all_failed_deliverables)} failed deliverables:")
        for d in all_failed_deliverables:
            console_err.print(f"- {d.full_id}")
        return 1

    return 0
