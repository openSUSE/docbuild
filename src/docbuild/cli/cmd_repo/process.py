"""Clone Git repositories from a stitchfile or a list of repository URLs."""

import asyncio
import logging
from pathlib import Path

from ...cli.context import DocBuildContext
from ...config.xml.stitch import create_stitchfile
from ...constants import GITLOGGER_NAME
from ...models.repo import Repo
from ...utils.contextmgr import make_timer
from ...utils.git import ManagedGitRepo

log = logging.getLogger(GITLOGGER_NAME)


async def process(context: DocBuildContext, repos: tuple[str, ...]) -> int:
    """Process the cloning of repositories.

    :param context: The DocBuildContext object containing configuration.
    :param repos: A tuple of repository selectors. If empty, all repos are used.
    :return: An integer exit code.
    :raises ValueError: If configuration paths are missing.
    """
    # The calling command function is expected to have checked context.envconfig.
    envcfg = context.envconfig
    config_dir_str = envcfg.paths.config_dir
    repo_dir_str = envcfg.paths.repo_dir

    configdir = Path(config_dir_str).expanduser()
    repo_dir = Path(repo_dir_str).expanduser()

    xmlconfigs = tuple(configdir.rglob("[a-z]*.xml"))
    stitchnode = await create_stitchfile(xmlconfigs)
    if stitchnode is None:
        raise ValueError("Stitch node could not be created.")

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

    # print(f'Found {len(unique_git_repos)} unique git repositories to process.')
    # print(f'Cloning repositories into {repo_dir}')

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
