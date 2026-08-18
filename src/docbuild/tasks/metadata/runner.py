"""Task orchestration and main entry point for metadata processing."""

import asyncio
from collections.abc import Sequence
import logging
from pathlib import Path

from aiostream import pipe, stream
from lxml import etree  # type: ignore
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


def get_deliverable_worker_limit(
    max_workers: int, deliverable_count: int
) -> int:
    """Resolve the concurrency limit for deliverable processing.

    :param max_workers: The maximum number of concurrent workers allowed.
    :param deliverable_count: Number of deliverables to process.
    :return: A worker limit between 1 and ``deliverable_count``.
    """
    if deliverable_count <= 0:
        return 1

    return max(1, min(max_workers, deliverable_count))


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
    """Process the doctypes and create metadata files using an aiostream pipeline.

    :param root: The stitched XML node containing configuration.
    :param doctype: The Doctype object to process.
    :param repo_dir: Path to the repository directory.
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

    # Sort deliverables alphabetically for predictable processing order
    deliverables.sort()

    if skip_repo_update:
        log.info("Skipping repository %s updates as requested.", repo_dir)
    else:
        await update_repositories(deliverables, repo_dir)

    worker_limit = get_deliverable_worker_limit(max_workers, len(deliverables))

    # Wrapper to catch exceptions safely and match the MapCallable signature
    async def process_deliverable_wrapper(
        deliverable: Deliverable, *args: object
    ) -> tuple[bool, Deliverable]:
        try:
            return await process_deliverable(
                deliverable,
                repo_dir,
                tmp_repo_dir,
                meta_cache_dir,
                dapstmpl=dapsmetatmpl,
                skip_repo_update=skip_repo_update,
            )
        except Exception as e:
            log.error("Error in task for %s: %s", deliverable.full_id, e)
            return False, deliverable

    # The elegant aiostream pipeline!
    pipeline = stream.iterate(deliverables) | pipe.map(
        process_deliverable_wrapper, task_limit=worker_limit, ordered=True
    )

    failed: list[Deliverable] = []

    try:
        # Evaluate the pipeline and collect results
        async with pipeline.stream() as streamer:
            async for success, deliverable in streamer:
                if not success:
                    failed.append(deliverable)
                    if exitfirst:
                        break  # Breaking automatically safely cancels pending tasks!
    except Exception as e:
        log.error("Task failed unexpectedly: %s", e)

    return failed


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

    :param main_portal_config: Path to the main portal XML configuration file.
    :param tmp_metadata_dir: Path to the temporary metadata directory.
    :param repo_dir: Path to the local repository directory.
    :param tmp_repo_dir: Path to the temporary worktree repository directory.
    :param meta_cache_dir: Path to metadata output cache.
    :param json_cache_dir: Path to JSON output cache.
    :param dapsmetatmpl: Template string for the DAPS metadata command.
    :param max_workers: Maximum number of concurrent deliverable workers.
    :param doctypes: A sequence of Doctype objects to process.
    :param exitfirst: If True, stop processing on the first failure.
    :param skip_repo_update: If True, skip updating Git repositories before processing.
    :return: 0 if all files passed validation, 1 if any failures occurred.
    """
    stitchnode: etree._ElementTree = await parse_portal_config(
        Path(main_portal_config).expanduser()
    )

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
