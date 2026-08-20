"""Runner for the build task."""

import asyncio
import logging
from pathlib import Path
import shlex
import tempfile
from typing import Any, Literal

from aiostream import pipe, stream
from lxml import etree  # type: ignore

from ...models.deliverable import Deliverable
from ...models.doctype import Doctype
from ...utils.contextmgr import PersistentOnErrorTemporaryDirectory
from ...utils.git import ManagedGitRepo
from ...utils.shell import run_command
from ..metadata.repos import update_repositories
from ..metadata.runner import get_deliverable_from_doctype, get_deliverable_worker_limit
from ..portal import parse_portal_config

log = logging.getLogger(__name__)


async def build_format(
    deliverable: Deliverable,
    fmt: Literal["html", "pdf", "single-html", "epub"],
    cwd: Path,
    build_dir: Path,
    daps_tmpl: str,
) -> tuple[bool, str]:
    """Execute the DAPS build command dynamically from a config template."""
    dcfile = deliverable.xml.dcfile
    assert dcfile is not None, "Deliverable must have a DC file."

    cmd_str = daps_tmpl.format(
        dcfile=dcfile,
        builddir=str(build_dir),
        format=fmt,
    )
    args = shlex.split(cmd_str)

    log.info("Building %s for %s...", fmt, deliverable.full_id)

    try:
        process = await run_command(args, cwd=cwd)
        if process.returncode == 0:
            log.info("Successfully built %s for %s", fmt, deliverable.full_id)
            log.info(" -> Artifacts stored in: %s", build_dir)
            return True, process.stdout

        log.error("Failed to build %s for %s:\n%s", fmt, deliverable.full_id, process.stderr)
        return False, process.stderr
    except Exception as e:
        log.error("Error executing daps for %s: %s", deliverable.full_id, e)
        return False, str(e)


async def process_deliverable_build(
    deliverable: Deliverable,
    repo_dir: Path,
    tmp_repo_dir: Path,
    tmp_build_base_dir: Path,
    daps_tmpls: dict[str, str],
) -> tuple[bool, Deliverable]:
    """Process a single deliverable: checkout worktree and build formats."""
    safe_id = deliverable.make_safe_name(deliverable.full_id)
    success = True

    # 1. Create temporary worktree (cleaned up automatically)
    async with PersistentOnErrorTemporaryDirectory(
        dir=tmp_repo_dir,
        prefix=f"wt_{safe_id}_",
    ) as worktree_dir:
        mg = ManagedGitRepo(deliverable.git.url, repo_dir)
        try:
            await mg.create_worktree(worktree_dir, deliverable.branch)
        except Exception as e:
            log.error("Failed to create worktree for %s: %s", deliverable.full_id, e)
            return False, deliverable

        cwd = Path(worktree_dir) / deliverable.subdir if deliverable.subdir else Path(worktree_dir)

        # 2. Build all enabled formats (output persists in tmp_build_base_dir)
        for fmt, is_enabled in deliverable.format.items():
            if is_enabled:
                tmpl = daps_tmpls.get(fmt, "daps -d {{dcfile}} --builddir {{builddir}} {{format}}")

                # Persist the output directory instead of auto-deleting it
                deliverable_build_dir = Path(tempfile.mkdtemp(
                    dir=tmp_build_base_dir,
                    prefix=f"build_{safe_id}_",
                    suffix=f"_{fmt}",
                ))

                fmt_success, _ = await build_format(
                    deliverable, fmt, cwd, deliverable_build_dir, tmpl
                )
                if not fmt_success:
                    success = False
                else:
                    # Call rsync to target directory
                    log.debug("Syncing result to ...")

    return success, deliverable


async def process_doctype(
    root: etree._ElementTree,
    doctype: Doctype,
    repo_dir: Path,
    tmp_repo_dir: Path,
    tmp_build_base_dir: Path,
    max_workers: int,
    daps_tmpls: dict[str, str],
    *,
    skip_repo_update: bool = False,
) -> list[Deliverable]:
    """Process a doctype and build its deliverables using aiostream."""
    deliverables: list[Deliverable] = await asyncio.to_thread(
        get_deliverable_from_doctype, root, doctype
    )

    deliverables = [deli for deli in deliverables if deli.xml.is_dc]
    deliverables.sort()

    if skip_repo_update:
        log.info("Skipping repository updates for %s as requested.", repo_dir)
    else:
        await update_repositories(deliverables, repo_dir)

    worker_limit = get_deliverable_worker_limit(max_workers, len(deliverables))

    async def build_wrapper(d: Deliverable, *args: object) -> tuple[bool, Deliverable]:
        try:
            return await process_deliverable_build(
                d, repo_dir, tmp_repo_dir, tmp_build_base_dir, daps_tmpls
            )
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
    tmp_repo_dir: Path,
    tmp_build_base_dir: Path,
    max_workers: int,
    doctypes: tuple[Doctype, ...] | list[Doctype],
    daps_tmpls: dict[str, str],
    *,
    skip_repo_update: bool = False,
) -> int:
    """Execute the build task pipeline."""
    root = await parse_portal_config(main_portal_config)

    tasks = [
        process_doctype(
            root, dt, repo_dir, tmp_repo_dir, tmp_build_base_dir, max_workers, daps_tmpls, skip_repo_update=skip_repo_update
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
