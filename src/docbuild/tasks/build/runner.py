"""Runner for the build task."""

import asyncio
import logging
from pathlib import Path
from typing import Any, Literal

from aiostream import pipe, stream
from lxml import etree  # type: ignore

from ...models.deliverable import Deliverable
from ...models.doctype import Doctype
from ...utils.shell import run_command
from ..metadata.repos import update_repositories
from ..metadata.runner import get_deliverable_from_doctype, get_deliverable_worker_limit
from ..portal import parse_portal_config

log = logging.getLogger(__name__)


async def build_format(
    deliverable: Deliverable,
    fmt: Literal["html", "pdf", "single-html", "epub"],
    cwd: Path,
) -> tuple[bool, str]:
    """Execute the DAPS build command for a specific format."""
    dcfile = deliverable.xml.dcfile
    if not dcfile:
        log.warning("No DC file found for %s, skipping %s build.", deliverable.full_id, fmt)
        return False, ""

    args = ["daps", "-d", dcfile, fmt]
    log.info("Building %s for %s...", fmt, deliverable.full_id)

    try:
        process = await run_command(args, cwd=cwd)
        if process.returncode == 0:
            log.info("Successfully built %s for %s", fmt, deliverable.full_id)
            return True, process.stdout

        log.error("Failed to build %s for %s:\n%s", fmt, deliverable.full_id, process.stderr)
        return False, process.stderr
    except Exception as e:
        log.error("Error executing daps for %s: %s", deliverable.full_id, e)
        return False, str(e)


async def process_deliverable_build(
    deliverable: Deliverable, repo_dir: Path
) -> tuple[bool, Deliverable]:
    """Process a single deliverable: build all its configured formats."""
    cwd = repo_dir / deliverable.subdir if deliverable.subdir else repo_dir

    success = True
    for fmt, is_enabled in deliverable.format.items():
        if is_enabled:
            fmt_success, _ = await build_format(deliverable, fmt, cwd)
            if not fmt_success:
                success = False

    return success, deliverable


async def process_doctype(
    root: etree._ElementTree,
    doctype: Doctype,
    repo_dir: Path,
    max_workers: int,
    *,
    skip_repo_update: bool = False,
) -> list[Deliverable]:
    """Process a doctype and build its deliverables using aiostream."""
    deliverables: list[Deliverable] = await asyncio.to_thread(
        get_deliverable_from_doctype, root, doctype
    )

    deliverables.sort()

    if skip_repo_update:
        log.info("Skipping repository updates for %s as requested.", repo_dir)
    else:
        await update_repositories(deliverables, repo_dir)

    worker_limit = get_deliverable_worker_limit(max_workers, len(deliverables))

    async def build_wrapper(d: Deliverable, *args: object) -> tuple[bool, Deliverable]:
        try:
            return await process_deliverable_build(d, repo_dir)
        except Exception as e:
            log.error("Build task error for %s: %s", d.full_id, e)
            return False, d

    pipeline: Any = stream.iterate(deliverables) | pipe.map(
        build_wrapper, task_limit=worker_limit, ordered=True  # type: ignore[arg-type]
    )

    failed: list[Deliverable] = []
    try:
        async with pipeline.stream() as streamer:
            async for success, deliverable in streamer:
                if not success:
                    failed.append(deliverable)
    except Exception as e:
        log.error("Pipeline failed unexpectedly: %s", e)

    return failed


async def process(
    main_portal_config: Path,
    repo_dir: Path,
    max_workers: int,
    doctypes: tuple[Doctype, ...] | list[Doctype],
    *,
    skip_repo_update: bool = False,
) -> int:
    """Execute the build task pipeline."""
    root = await parse_portal_config(main_portal_config)

    tasks = [
        process_doctype(
            root, dt, repo_dir, max_workers, skip_repo_update=skip_repo_update
        )
        for dt in doctypes
    ]
    results_per_doctype = await asyncio.gather(*tasks)

    all_failed = [d for failed_list in results_per_doctype for d in failed_list]

    if all_failed:
        log.error("Build completed with %d failures.", len(all_failed))
        return 1

    log.info("All deliverables built successfully!")
    return 0
