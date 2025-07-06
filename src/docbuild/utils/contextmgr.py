"""Provides context managers."""

from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
import time


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
