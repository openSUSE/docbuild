"""Git helper function."""
import asyncio
from pathlib import Path
from typing import IO, Any


async def clone_from_repo(
    repo_path: Path,
    worktree_dir: Path,
    branch: str,
    *,
    is_local: bool = True,
    stdout: int | IO[Any] | None = None,
    stdin: int | IO[Any] | None = asyncio.subprocess.DEVNULL,
    stderr: int | IO[Any] | None = asyncio.subprocess.PIPE,
    options: list[str] | None = None,
) -> Path:
    """Create a temporary clone of a bare repository.

    :param branch: The branch to use when cloning.
    :param repo_path: The path to the bare repository.
    :param worktree_dir: The path to the target directory.
    :param is_local: Clone from a local machine, bypasses the normal
      "Git aware" transport mechanism, see man "git clone".
    :param options: A list of additional options for the git clone command.
    :return: The path to the created worktree.
    :raise RuntimeError: If the clone fails.
    """
    clone_cmd = ['git', 'clone']
    if is_local:
        clone_cmd.append('--local')

    clone_cmd.extend(['--branch', branch])

    if options:
        clone_cmd.extend(options)

    clone_cmd.extend([str(repo_path), str(worktree_dir)])

    clone_process = await asyncio.create_subprocess_exec(
        *clone_cmd,
        stdout=stdout,
        stdin=stdin,
        stderr=stderr,
    )
    _, stderr_bytes = await clone_process.communicate()
    if clone_process.returncode != 0:
        # Raise an exception on failure to let the context manager know.
        error_message = 'Unknown error'
        if stderr_bytes:
            error_message = stderr_bytes.decode().strip()
        raise RuntimeError(
            f'Failed to clone {repo_path}: {error_message}'
        )
    return worktree_dir

