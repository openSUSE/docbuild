"""Repository synchronization helpers shared across task implementations."""

from collections.abc import Iterable
import logging
from pathlib import Path

from ...utils.concurrency import TaskFailedError, run_parallel
from ...utils.git import ManagedGitRepo

log = logging.getLogger(__name__)


async def update_managed_repositories(
    repo_dir: Path,
    repo_urls: Iterable[str],
    updated_repos: set[str],
    *,
    limit: int,
) -> list[str]:
    """Update bare repositories once per remote URL.

    :param repo_dir: Root directory for bare repositories.
    :param repo_urls: Repository URLs to update.
    :param updated_repos: Repository URLs already updated during this run.
    :param limit: Maximum number of concurrent repo updates.
    :return: Slugs for repositories updated successfully in this call.
    """
    repos_to_update: list[ManagedGitRepo] = []
    for repo_url in repo_urls:
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
