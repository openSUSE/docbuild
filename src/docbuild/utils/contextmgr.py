"""Provides context managers."""

import asyncio
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager, suppress
from dataclasses import dataclass
import json
import logging
import os
from pathlib import Path
import shutil
import tempfile
import time
from types import TracebackType
from typing import Any
import weakref as _weakref

# Type aliases for exception handling
type ExcType = type[BaseException] | None
type ExcVal = BaseException | None
type ExcTback = TracebackType | None

# Logging
log = logging.getLogger(__name__)

@dataclass
class TimerData:
    """Data structure to hold timer information."""

    name: str
    start: float = float('nan')
    end: float = float('nan')
    elapsed: float = float('nan')


def make_timer(
    name: str, method: Callable[[], float] = time.perf_counter
) -> Callable[[], AbstractContextManager[TimerData]]:
    """Create independant context managers to measure elapsed time.

    Each timer is independent and can be used in a context manager.
    The name is used to identify the timer.

    :param name: Name of the timer.
    :param method: A callable that returns a float, used for measuring time.
        Defaults to :func:`time.perf_counter`.
    :return: A callable that returns a context manager. The context manager
        yields a :class:`TimerData` object.

    .. code-block:: python

        timer = make_timer('example_timer')

        with timer() as timer_data:
            # Code to be timed
            pass

        timer_data.elapsed  # Access the elapsed time
    """

    @contextmanager
    def wrapper() -> Iterator[TimerData]:
        """Context manager to measure elapsed time."""
        data = TimerData(name=name)
        data.start = method()
        try:
            yield data
        finally:
            data.end = method()
            data.elapsed = data.end - data.start

    return wrapper


class PersistentOnErrorTemporaryDirectory(tempfile.TemporaryDirectory):
    """A temporary directory that supports both sync and async usage.

    It deletes the temporary directory only if no exception occurs within the
    context block. This is useful for debugging, as it preserves the directory
    and its contents for inspection after an error.

    It is a subclass of :class:`tempfile.TemporaryDirectory` and mimics its
    initializer.

    .. code-block:: python

        # Synchronous usage
        with PersistentOnErrorTemporaryDirectory() as temp_dir:
            # temp_dir is a Path object
            ...

        # Asynchronous usage
        async with PersistentOnErrorTemporaryDirectory() as temp_dir:
            # temp_dir is a Path object
            ...

    Optional arguments:
    :param suffix: A str suffix for the directory name.  (see mkdtemp)
    :param prefix: A str prefix for the directory name.  (see mkdtemp)
    :param dir: A directory to create this temp dir in.  (see mkdtemp)
    """

    def __init__(
        self,
        suffix: str | None = None,
        prefix: str | None = None,
        dir: str | Path | None = None,  # noqa: A002
    ) -> None:
        # Call the parent constructor. We don't need the
        # `ignore_cleanup_errors` flag as we implement our own cleanup.
        super().__init__(suffix=suffix, prefix=prefix, dir=dir)

    def __enter__(self) -> Path:
        """Enter the runtime context and create the temporary directory.

        :returns: Path to the created temporary directory.
        """
        # The parent __enter__ returns a string, so we override it
        # to return a Path object for consistency with your original class.
        return Path(self.name)

    async def __aenter__(self) -> Path:
        """Enter the async runtime context and create the temporary directory.

        :returns: Path to the created temporary directory.
        """
        # The underlying directory creation is synchronous.
        return self.__enter__()

    def __exit__(self, exc_type: ExcType, exc_val: ExcVal, exc_tb: ExcTback) -> None:
        """Exit the runtime context and delete the directory if no exception occurred.

        :param exc_type: Exception type, if any.
        :param exc_val: Exception instance, if any.
        :param exc_tb: Traceback, if any.
        """
        # DEPENDENCY: this is being called in async context from __aexit__.
        #
        # CRITICAL: We must always detach the finalizer. If we don't,
        # and an error occurred, the directory would still be deleted
        # upon garbage collection, which is not what we want.
        self._finalizer.detach()

        if exc_type is None:
            # No exception occurred in the `with` block, so we clean up.
            try:
                shutil.rmtree(self.name)

            except OSError as e:
                # Your custom logging is more informative than the parent's
                # `ignore_errors=True`, so we replicate it here.
                log.exception('Failed to delete temp dir %s: %s', self.name, e)

    async def __aexit__(self,
        exc_type: ExcType,
        exc_val: ExcVal,
        exc_tb: ExcTback
    ) -> None:
        """Asynchronously clean up the directory on successful exit.

        Async exit the runtime context and delete the directory if no
        exception occurred.

        :param exc_type: Exception type, if any.
        :param exc_val: Exception instance, if any.
        :param exc_tb: Traceback, if any.
        """
        await asyncio.to_thread(self.__exit__, exc_type, exc_val, exc_tb)


@contextmanager
def edit_json(path: Path | str) -> Iterator[dict[str, Any]]:
    """Context manager for safely and atomically editing a JSON file.

    This function implements a "read-modify-write" cycle with ACID-like properties.
    It ensures that the file is either fully updated or remains strictly unchanged
    (no partial writes or corruption) if an error occurs during modification or saving.

    The operation follows three phases:

    1. **Read**: The file is parsed into a Python dictionary.
    2. **Modify** (Yield): Control is handed to the caller to modify the dictionary.
    3. **Write**:
       - If the block exits successfully, the data is written to a temporary file,
         fsync-ed to disk, and atomically renamed over the original file.
       - If an exception is raised within the block, the write phase is skipped
         entirely.

    :param path: The path to the JSON file to edit.
    :yields: The content of the JSON file as a mutable dictionary.

    :raises FileNotFoundError: If the specified ``path`` does not exist.
    :raises json.JSONDecodeError: If the file exists but contains invalid JSON.
    :raises OSError: If an I/O error occurs during reading, writing, or fsyncing.

    Example usage:

    .. code-block:: python

        with edit_json('config.json') as data:
            config["docs"][0]["dcfile"] = path.name
            config["docs"][0]["format"]["html"] = "..."
            # more modifications...
    """
    encoding = 'utf-8'
    path = Path(path)
    parent = path.parent

    # Load JSON
    with path.open('r', encoding=encoding) as f:
        data = json.load(f)

    # Hand control to the user
    try:
        yield data
    except BaseException:
        # Don't write anything; re-raise to preserve original exception
        raise

    # --- Commit phase (only reached if no exception occurred) ---

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            'w',
            encoding=encoding,
            dir=str(parent),
            delete=False,  # We manage deletion manually
            prefix=f'.{path.stem}.',
            suffix='.tmp',
        ) as tmp_file:
            tmp_path = Path(tmp_file.name)

            # Write & Flush
            json.dump(data, tmp_file, indent=4)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())

        # Permissions
        with suppress(FileNotFoundError):
            tmp_path.chmod(path.stat().st_mode)

        # Atomic Replace
        tmp_path.replace(path)

        # Directory Sync (Durability) on POSIX
        with suppress(OSError):
            dir_fd = os.open(str(parent), os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)

        # Mark as successful to skip cleanup
        tmp_path = None

    finally:
        # Cleanup temporary file on failure
        # If tmp_path is not None, it means we crashed before the replace.
        if tmp_path and tmp_path.exists():
            with suppress(OSError):
                tmp_path.unlink()
