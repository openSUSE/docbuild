"""Provides context managers."""

from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
import logging
from pathlib import Path
import shutil
import tempfile
import time
from types import TracebackType
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
    """Delete temporary directory only if no exception occurs.

    It is similar to :class:`tempfile.TemporaryDirectory`, but it does not
    delete the directory if an exception occurs. This is useful for debugging
    or when you want to inspect the contents of the directory after an error.

    .. code-block:: python

        with PersistentOnErrorTemporaryDirectory() as temp_dir:
            # Do something with the temporary directory, it's a Path object

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

    def __exit__(self, exc_type: ExcType, exc_val: ExcVal, exc_tb: ExcTback) -> None:
        """Exit the runtime context and delete the directory if no exception occurred.

        :param exc_type: Exception type, if any.
        :param exc_val: Exception instance, if any.
        :param exc_tb: Traceback, if any.
        """
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
