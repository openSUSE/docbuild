"""Shell command utilities."""

import asyncio
from collections.abc import Sequence
import logging
from pathlib import Path
from subprocess import CompletedProcess

from ..constants import GIT_CONFIG_FILENAME, GITLOGGER_NAME

log = logging.getLogger(GITLOGGER_NAME)


async def run_command(
    args: Sequence[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> CompletedProcess:
    """Run an external command and capture its output.

    :param args: The command and its arguments separated as tuple elements.
    :param cwd: The working directory for the command.
    :param env: A dictionary of environment variables for the new process.
    :return: a :class:`~subprocess.CompletedProcess` object.
    :raises FileNotFoundError: if the command is not found.
    """
    # 1. Start the subprocess and connect the pipes
    # We always pipe because we must return the output strings.
    process = await asyncio.create_subprocess_exec(
        args[0], *args[1:],
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    # 2. Wait for the process to finish
    bstdout, bstderr = await process.communicate()

    # 3. Decode and return the result
    return CompletedProcess(
        args=args,
        returncode=process.returncode or 0,
        stdout=bstdout.decode('utf-8').strip(),
        stderr=bstderr.decode('utf-8').strip(),
    )


async def execute_git_command(
    *args: str,
    cwd: Path | None = None,
    extra_env: dict[str, str] | None = None,
    gitconfig: Path | None = None,
) -> CompletedProcess[str]:
    """Execute a Git command asynchronously in a given directory.

    :param args: Command arguments for Git.
    :param cwd: The working directory for the Git command. If None, the
        current working directory is used.
    :param extra_env: Additional environment variables to set for the command.
    :param gitconfig: The path to a separate Git configuration file. If None,
        the default config from etc/git/gitconfig is used.
    :return: a :class:`~subprocess.CompletedProcess` object.
    :raises RuntimeError: If the command fails.
    :raises FileNotFoundError: If `cwd` is specified but does not exist.
    """
    if cwd and not cwd.is_dir():
        raise FileNotFoundError(f'Git working directory not found: {cwd}')

    # Determine which config file to use
    gconfig = gitconfig if gitconfig else GIT_CONFIG_FILENAME

    # Default Git arguments for consistent behavior
    git_config_args = ('-c', 'color.ui=never')
    command = ('git', *git_config_args, *args)
    log.debug('Executing Git command: %s in %s', ' '.join(command), cwd)

    # Default environment for secure and non-interactive execution
    default_env = {
        'LANG': 'C',
        'LC_ALL': 'C',
        'GIT_TERMINAL_PROMPT': '0',
        'GIT_PROGRESS_FORCE': '1',
        'GIT_CONFIG_SYSTEM': '/dev/null',
        # 'GIT_CONFIG_NOSYSTEM': '1',  # For older Git versions
        'GIT_CONFIG_GLOBAL': str(gconfig),
    }

    # Merge environments, allowing kwargs to override defaults
    merged_env = {**default_env, **(extra_env or {})}

    # Delegate execution to the generic run_command utility
    process = await run_command(
        command,
        cwd=cwd,
        env=merged_env,
    )

    if process.returncode != 0:
        raise RuntimeError(
            f'Git command failed with exit code {process.returncode}: '
            f'{" ".join(command)}\nStderr: {process.stderr}'
        )

    return process
