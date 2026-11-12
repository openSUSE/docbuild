"""Git repository management for metadata processing."""

import asyncio
from contextlib import nullcontext
import logging
from pathlib import Path

from docbuild.models.deliverable import Deliverable
from docbuild.utils.display import get_live_manager
from docbuild.utils.git import ManagedGitRepo

log = logging.getLogger(__name__)


async def update_repositories(
    deliverables: list[Deliverable], bare_repo_dir: Path
) -> bool:
    """Update all Git repositories associated with the deliverables.

    :param deliverables: A list of Deliverable objects.
    :param bare_repo_dir: The root directory for storing permanent bare clones.
    :return: ``True`` if all repositories updated successfully, ``False`` otherwise.
    """
    log.info("Updating Git repositories...")
    repo_map = {
        d.git.url: d.git.name
        for d in deliverables
        if d.git is not None
    }
    unique_urls = sorted(set(repo_map.keys()))

    if not unique_urls:
        return True

    manager = get_live_manager()
    stage = manager._active if manager else None
    if stage and (stage._total is None or stage._total == 0):
        stage.set_total(len(unique_urls))

    repos = [ManagedGitRepo(url, bare_repo_dir) for url in unique_urls]

    async def clone_one(repo: ManagedGitRepo) -> bool:
        """Clone the given Git repository as a bare repository."""
        label = repo_map.get(repo.remote_url, repo.slug)
        item_ctx = stage.item(label) if stage else nullcontext()
        with item_ctx as item:
            try:
                res = await repo.clone_bare()
                if item and not res:
                    item.fail()
                return bool(res)
            except Exception:
                if item:
                    item.fail()
                raise

    tasks = [
        asyncio.create_task(clone_one(repo), name=f"update:{repo_map.get(repo.remote_url, repo.slug)}")
        for repo in repos
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    res = True
    for repo, result in zip(repos, results, strict=False):
        if isinstance(result, Exception) or not result:
            log.error("Failed to update repository %s", repo.slug)
            res = False

    return res
