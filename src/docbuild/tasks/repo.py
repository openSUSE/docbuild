"""Logic for repository management tasks."""

import asyncio
import logging
from pathlib import Path

from docbuild.cli.cmd_portal.process import parse_portal_config
from docbuild.constants import GITLOGGER_NAME
from docbuild.models.repo import Repo
from docbuild.utils.contextmgr import make_timer
from docbuild.utils.git import ManagedGitRepo

log = logging.getLogger(GITLOGGER_NAME)


async def clone_repositories(
    main_portal_config: Path,
    repo_dir: Path,
    repos: tuple[str, ...]
) -> int:
    """Process the cloning of repositories.

    :param main_portal_config: Path to the main portal config XML.
    :param repo_dir: Path to the directory where bare repos should be stored.
    :param repos: A tuple of repository selectors. If empty, all repos are used.
    :return: An integer exit code (0 for success, 1 for failure).
    """
    stitchnode = await parse_portal_config(main_portal_config)

    if not repos:
        git_nodes = await asyncio.to_thread(stitchnode.xpath, ".//git")
        all_remotes = [
            Repo(repo.attrib.get("remote"))
            for repo in git_nodes
            if repo.attrib.get("remote") is not None
        ]
        # Create a unique list while preserving order
        unique_git_repos = list(dict.fromkeys(all_remotes))
    else:
        # Create a unique list from user input, preserving order
        unique_git_repos = list(dict.fromkeys(Repo(r) for r in repos))
        log.debug("User-specified repositories: %s", unique_git_repos)

    if not unique_git_repos:
        log.info("No repositories found to clone.")
        return 0

    timer = make_timer("git-clone-repos")
    with timer() as t:
        tasks = [
            ManagedGitRepo(str(repo), repo_dir).clone_bare()
            for repo in unique_git_repos
        ]
        results = await asyncio.gather(*tasks)

    log.info("Elapsed time:  %0.3f seconds", t.elapsed)

    # Return 0 for success (all clones succeeded), 1 for failure.
    if all(results):
        return 0
    return 1
