"""Shared worktree lifecycle helpers for repository-backed tasks."""

from collections.abc import AsyncIterator, Iterable
from contextlib import AsyncExitStack, asynccontextmanager
import logging
from pathlib import Path
import time

from ...utils.concurrency import TaskFailedError, run_parallel
from ...utils.contextmgr import PersistentOnErrorTemporaryDirectory
from ...utils.git import ManagedGitRepo

log = logging.getLogger(__name__)


@asynccontextmanager
async def shared_worktrees(
    repo_dir: Path,
    tmp_repo_dir: Path,
    repo_branches: Iterable[tuple[str, str]],
    *,
    limit: int,
) -> AsyncIterator[dict[tuple[str, str], Path]]:
    """Create temporary shared worktrees keyed by repository URL and branch.

    :param repo_dir: Root directory for bare repositories.
    :param tmp_repo_dir: Parent directory for temporary worktrees.
    :param repo_branches: Pairs of repository URLs and branches to prepare.
    :param limit: Maximum number of concurrent worktree creations.
    :yield: Mapping of ``(repo_url, branch)`` to temporary worktree paths.
    """
    worktrees: dict[tuple[str, str], Path] = {}

    async with AsyncExitStack() as stack:
        worktree_jobs: list[tuple[ManagedGitRepo, str, Path]] = []
        for repo_url, branch in repo_branches:
            repo = ManagedGitRepo(repo_url, repo_dir)
            temp_dir_ctx = PersistentOnErrorTemporaryDirectory(
                dir=str(tmp_repo_dir),
                prefix=f"shared-wt-{repo.slug}",
            )
            worktree_dir = await stack.enter_async_context(temp_dir_ctx)
            worktree_jobs.append((repo, branch, worktree_dir))

        async def create_worktree(
            job: tuple[ManagedGitRepo, str, Path],
        ) -> tuple[str, str, Path, float]:
            repo, branch, worktree_dir = job
            started_at = time.perf_counter()
            await repo.create_worktree(worktree_dir, branch)
            return (
                repo.remote_url,
                branch,
                worktree_dir,
                time.perf_counter() - started_at,
            )

        worktree_limit = max(1, min(limit, len(worktree_jobs))) if worktree_jobs else 1
        async for result in run_parallel(
            worktree_jobs,
            create_worktree,
            limit=worktree_limit,
        ):
            if isinstance(result, TaskFailedError):
                log.error(
                    "Failed to create shared worktree for %s: %s",
                    result.item[0].remote_url,
                    result.original_exception,
                )
                continue

            repo_url, branch, worktree_dir, elapsed = result
            log.info(
                "Shared worktree creation for %s (branch %s) took %.3fs",
                repo_url,
                branch,
                elapsed,
            )
            worktrees[(repo_url, branch)] = worktree_dir

        yield worktrees
