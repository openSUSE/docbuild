"""Shell command utilities."""

import asyncio
import logging
from pathlib import Path

from ..constants import GIT_CONFIG_FILENAME, GITLOGGER_NAME

log = logging.getLogger(GITLOGGER_NAME)


async def run_command(
    *args: str,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> tuple[int, str, str]:
    """Run an external command and capture its output.

    :param args: The command and its arguments separated as tuple elements.
    :param cwd: The working directory for the command.
    :param env: A dictionary of environment variables for the new process.
    :return: A tuple of (returncode, stdout, stderr).
    :raises FileNotFoundError: if the command is not found.
    """
    process = await asyncio.create_subprocess_exec(
        *args,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    stdout, stderr = await process.communicate()

    # After .communicate() returns, the process has terminated and the
    # returncode is guaranteed to be set to an integer.
    assert process.returncode is not None

    return process.returncode, stdout.decode(), stderr.decode()


async def execute_git_command(
    *args: str,
    cwd: Path | None = None,
    extra_env: dict[str, str] | None = None,
    gitconfig: Path | None = None,
) -> tuple[str, str]:
    """Execute a Git command asynchronously in a given directory.

    :param args: Command arguments for Git.
    :param cwd: The working directory for the Git command. If None, the
        current working directory is used.
    :param extra_env: Additional environment variables to set for the command.
    :param gitconfig: The path to a separate Git configuration file. If None,
        the default config from etc/git/gitconfig is used.
    :return: A tuple containing the decoded stdout and stderr of the command.
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
    returncode, stdout, stderr = await run_command(
        *command,
        cwd=cwd,
        env=merged_env,
    )

    if returncode != 0:
        raise RuntimeError(
            f'Git command failed with exit code {returncode}: '
            f'{" ".join(command)}\nStderr: {stderr}'
        )

    return stdout.strip(), stderr.strip()
