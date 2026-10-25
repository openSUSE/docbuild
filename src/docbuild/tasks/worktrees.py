"""Task-level Git worktree orchestration."""

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable
import logging
from pathlib import Path

from aiostream import pipe, stream

from ..models.deliverable import Deliverable
from ..utils.contextmgr import PersistentOnErrorTemporaryDirectory
from ..utils.git import ManagedGitRepo
from .metadata.runner import get_deliverable_worker_limit

log = logging.getLogger(__name__)


async def _safe_process_one(
    d: Deliverable,
    wt_dir: str,
    semaphore: asyncio.Semaphore,
    process_single_func: Callable[[Deliverable, str], Awaitable[tuple[bool, Deliverable]]],
) -> tuple[bool, Deliverable]:
    """Safely process a single deliverable using the provided function and semaphore."""
    try:
        async with semaphore:
            return await process_single_func(d, wt_dir)
    except (OSError, KeyError, ValueError) as exc:
        log.error("Unexpected error for %s: %s", d.full_id, exc)
        return False, d
    except Exception as exc:
        log.error("Fatal error for %s: %s", d.full_id, exc)
        return False, d


async def _process_group(
    group_item: tuple[tuple[str, str], list[Deliverable]],
    repo_dir: Path,
    tmp_repo_dir: Path,
    build_limit: int,
    semaphore: asyncio.Semaphore,
    process_single_func: Callable[[Deliverable, str], Awaitable[tuple[bool, Deliverable]]],
) -> list[Deliverable]:
    """Process a single repository group within an isolated worktree."""
    group_key, group_deliverables = group_item
    repo_url, branch = group_key
    safe_prefix = f"wt_{group_deliverables[0].make_safe_name(group_deliverables[0].full_id)}_grp{len(group_deliverables)}_"

    async with PersistentOnErrorTemporaryDirectory(dir=tmp_repo_dir, prefix=safe_prefix) as wt_dir:
        mg = ManagedGitRepo(repo_url, repo_dir)
        try:
            await mg.create_worktree(wt_dir, branch)
        except Exception as e:
            log.error("Failed to create worktree for %s branch %s: %s", repo_url, branch, e)
            return group_deliverables

        async def process_mapped(d: Deliverable) -> tuple[bool, Deliverable]:
            return await _safe_process_one(d, wt_dir, semaphore, process_single_func)

        pipeline = stream.iterate(group_deliverables) | pipe.map(
            process_mapped,
            task_limit=build_limit,
            ordered=True,
        )

        failed_in_group = []
        try:
            async with pipeline.stream() as streamer:
                async for success, d in streamer:
                    if not success:
                        failed_in_group.append(d)
        except Exception as e:
            log.error("Group pipeline failed: %s", e)
            failed_in_group.extend(group_deliverables)

        return failed_in_group


async def process_with_shared_worktrees(
    deliverables: list[Deliverable],
    repo_dir: Path,
    tmp_repo_dir: Path,
    max_workers: int,
    semaphore: asyncio.Semaphore,
    process_single_func: Callable[[Deliverable, str], Awaitable[tuple[bool, Deliverable]]],
) -> list[Deliverable]:
    """Group deliverables by repo/branch and create a shared Git worktree per group.

    Process them concurrently using a global semaphore to cap active workers.
    """
    groups: dict[tuple[str, str], list[Deliverable]] = defaultdict(list)
    failed: list[Deliverable] = []

    for d in deliverables:
        # Prevent failure on deliverables missing Git config
        if not getattr(d, "git", None) or not getattr(d.git, "url", None):
            log.error("Deliverable %s is missing Git remote configuration. Skipping.", d.full_id)
            failed.append(d)
            continue
        groups[(d.git.url, d.branch)].append(d)

    if not groups:
        return failed

    group_limit = get_deliverable_worker_limit(max_workers, len(groups))
    build_limit = get_deliverable_worker_limit(max_workers, len(deliverables))

    async def mapped_process_group(item: tuple[tuple[str, str], list[Deliverable]]) -> list[Deliverable]:
        return await _process_group(
            item, repo_dir, tmp_repo_dir, build_limit, semaphore, process_single_func
        )

    pipeline = stream.iterate(list(groups.items())) | pipe.map(
        mapped_process_group, task_limit=group_limit, ordered=True
    )

    try:
        async with pipeline.stream() as streamer:
            async for group_failed in streamer:
                failed.extend(group_failed)
    except Exception as e:
        log.error("Global pipeline failed: %s", e)
        failed.extend([d for ds in groups.values() for d in ds])

    return failed
