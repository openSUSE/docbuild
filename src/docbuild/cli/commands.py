""" """

import asyncio
from collections.abc import Mapping, Sequence
import os
import shutil
from subprocess import CompletedProcess
from typing import IO, Any, cast

# Type aliases for better readability
type StrOrBytesPath = str | bytes | os.PathLike[str] | os.PathLike[bytes]
type _TXT = str | bytes
type _ENV = Mapping[bytes, _TXT] | Mapping[str, _TXT]
type AnyPath = str | bytes | os.PathLike[str] | os.PathLike[bytes]
type _CMD = _TXT | Sequence[AnyPath]


def resolve_command(program: StrOrBytesPath, *args: StrOrBytesPath) -> tuple[str, ...]:
    """Resolve the program to an absolute path and return the full command tuple.

    If the program is already an absolute path, it is used as is. Otherwise,
    it is searched for in the system's PATH.

    :param program: The program to execute.
    :param args: The arguments to pass to the program.
    :return: A tuple containing the resolved program path and the arguments.
    :raises FileNotFoundError: If the program is not found or not executable.
    """
    # shutil.which can handle absolute paths, so we don't need to check for them.
    # It will return the path if it's executable, or None otherwise.
    resolved_program = shutil.which(str(program))

    if resolved_program is None:
        raise FileNotFoundError(
            f"Program '{program}' not found in PATH or not executable."
        )

    # Cast args to string to create a uniform tuple
    str_args = tuple(str(arg) for arg in args)
    return (resolved_program, *str_args)


async def run_command(
    program: StrOrBytesPath,
    *args: StrOrBytesPath,
    stdin: IO[Any] | int | None = None,
    stdout: IO[Any] | int | None = None,
    stderr: IO[Any] | int | None = None,
    cwd: StrOrBytesPath | None = None,
    env: _ENV | None = None,
    **kwds,  # noqa: ANN003
) -> CompletedProcess:
    """Run a command asynchronously and return the result.

    :param program: The command to run.
    :param args: The arguments to pass to git.
    :param stdin: The standard input stream to use.
    :param stdout: The standard output stream to use.
    :param stderr: The standard error stream to use.
    :param cwd: The working directory to run the command in.
    :param env: The environment variables to pass to the command.
    :param kwds: Additional keyword arguments to pass to the subprocess.
    :return: The class:`~subprocess.CompletedProcess` object.
    """
    program = str(program)
    args = tuple(str(arg) for arg in args)
    clone_process = await asyncio.create_subprocess_exec(
        program,
        *args,
        cwd=cwd,
        env=env,
        stdin=stdin,
        stderr=stderr,
        stdout=stdout,
        **kwds,
    )
    stdout_data, stderr_data = await clone_process.communicate()
    return CompletedProcess(
        args=[program, *args],
        returncode=cast(int, clone_process.returncode),
        stdout=stdout_data.decode() if stdout_data else None,
        stderr=stderr_data.decode() if stderr_data else None,
    )


async def run_git(
    *args: StrOrBytesPath,
    cwd: StrOrBytesPath | None = None,
    env: _ENV | None = None,
    **kwds,  # noqa: ANN003
) -> CompletedProcess:
    """Run a git command asynchronously.

    The :command:`git` command is expected to be in the system PATH.

    :param args: The arguments to pass to git without the command.
    :param cwd: The working directory to run the command in.
    :param env: The environment variables to pass to the command.
    :param kwds: Additional keyword arguments to pass to the subprocess.
    :return: The class:`~subprocess.CompletedProcess` object.
    :raise FileNotFoundError: If the git executable is not found in PATH.
    """
    program, *resolved_args = resolve_command('git', *args)

    return await run_command(
        program,
        *resolved_args,
        cwd=cwd,
        env=env,
        **kwds,
    )


async def run_daps(
    *args: StrOrBytesPath,
    cwd: StrOrBytesPath | None = None,
    env: _ENV | None = None,
    **kwds,  # noqa: ANN003
) -> CompletedProcess:
    """Run the DAPS command asynchronously.

    The :command:`daps` command is expected to be in the system PATH.

    :param args: The arguments to pass to DAPS without the command.
    :param cwd: The working directory to run the command in.
    :param env: The environment variables to pass to the command.
    :param kwds: Additional keyword arguments to pass to the subprocess.
    :return: The class:`~subprocess.CompletedProcess` object.
    :raises FileNotFoundError: If the DAPS executable is not found in PATH.
    """
    program, *resolved_args = resolve_command('daps', *args)

    return await run_command(
        program,
        *resolved_args,
        cwd=cwd,
        env=env,
        **kwds,
    )
