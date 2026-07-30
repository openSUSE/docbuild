"""Git repository management for metadata processing."""

import asyncio
import logging
from pathlib import Path

from docbuild.models.deliverable import Deliverable
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
    unique_urls = {d.git.url for d in deliverables}
    repos = [ManagedGitRepo(url, bare_repo_dir) for url in unique_urls]

    tasks = [repo.clone_bare() for repo in repos]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    res = True
    for repo, result in zip(repos, results, strict=False):
        if isinstance(result, Exception) or not result:
            log.error("Failed to update repository %s", repo.slug)
            res = False

    return res
