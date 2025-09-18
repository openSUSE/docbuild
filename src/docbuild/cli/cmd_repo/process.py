"""Clone Git repositories from a stitchfile or a list of repository URLs."""

import asyncio
import logging
from pathlib import Path

from ...cli.context import DocBuildContext
from ...config.xml.stitch import create_stitchfile
from ...models.repo import Repo
from ...utils.contextmgr import make_timer
from ...constants import GITLOGGER_NAME

log = logging.getLogger(GITLOGGER_NAME)


async def clone_repo(repo: Repo, base_dir: Path) -> bool:
    """Clone a GitHub repository into the specified base directory."""
    repo_path = base_dir / repo.slug

    # Ensure the parent directory exists
    repo_path.parent.mkdir(parents=True, exist_ok=True)

    if repo_path.exists():
        log.info('Repository %r already exists at %s', repo.name, repo_path)
        return True

    log.info("Cloning '%s' into '%s'...", repo, str(repo_path))

    # Use create_subprocess_exec for security (avoids shell injection)
    # and pass arguments as a sequence.
    cmd_args = [
        'git',
        '-c',
        'color.ui=never',
        'clone',
        '--bare',
        '--progress',
        str(repo),
        str(repo_path),
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd_args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={
            'LANG': 'C',
            'LC_ALL': 'C',
            'GIT_TERMINAL_PROMPT': '0',
            'GIT_PROGRESS_FORCE': '1',
        },
    )

    # Wait for the process to finish and capture output
    stdout, stderr = await process.communicate()

    if process.returncode == 0:
        log.info("Cloned '%s' successfully", repo)
        return True
    else:
        log.error(
            "Failed to clone '%s' (exit code %i)",
            repo,
            process.returncode,
        )
        if stderr:
            # Log each line of stderr with a prefix for better readability
            error_output = stderr.decode().strip()
            for line in error_output.splitlines():
                log.error('  [git] %s', line)
        return False


async def process(context: DocBuildContext, repos: tuple[str, ...]) -> int:
    """Process the cloning of repositories.

    :param context: The DocBuildContext object containing configuration.
    :param repos: A tuple of repository selectors. If empty, all repos are used.
    :return: An integer exit code.
    :raises ValueError: If configuration paths are missing.
    """
    # The calling command function is expected to have checked context.envconfig.
    paths = context.envconfig.get('paths', {})
    config_dir_str = paths.get('config_dir')
    repo_dir_str = paths.get('repo_dir')

    if not config_dir_str:
        raise ValueError('Could not get a value from envconfig.paths.config_dir')
    if not repo_dir_str:
        raise ValueError('Could not get a value from envconfig.paths.repo_dir')

    configdir = Path(config_dir_str).expanduser()
    repo_dir = Path(repo_dir_str).expanduser()

    xmlconfigs = tuple(configdir.rglob('[a-z]*.xml'))
    stitchnode = await create_stitchfile(xmlconfigs)
    if stitchnode is None:
        raise ValueError('Stitch node could not be created.')

    if not repos:
        git_nodes = await asyncio.to_thread(stitchnode.xpath, './/git')
        all_remotes = [
            Repo(repo.attrib.get('remote'))
            for repo in git_nodes
            if repo.attrib.get('remote') is not None
        ]
        # Create a unique list while preserving order
        unique_git_repos = list(dict.fromkeys(all_remotes))
    else:
        # Create a unique list from user input, preserving order
        unique_git_repos = list(dict.fromkeys(Repo(r) for r in repos))

    if not unique_git_repos:
        log.info('No repositories found to clone.')
        return 0

    # print(f'Found {len(unique_git_repos)} unique git repositories to process.')
    # print(f'Cloning repositories into {repo_dir}')

    timer = make_timer('git-clone-repos')
    with timer() as t:
        tasks = [clone_repo(repo, repo_dir) for repo in unique_git_repos]
        results = await asyncio.gather(*tasks)

    log.info('Elapsed time:  %0.3f seconds', t.elapsed)

    # Return 0 for success (all clones succeeded), 1 for failure.
    if all(results):
        return 0
    return 1