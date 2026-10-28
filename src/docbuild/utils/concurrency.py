"""Concurrency utilities using producer-consumer patterns.

This module provides helpers for managing concurrent asyncio tasks with
strict concurrency limits, backpressure handling, and exception tracking.

The producer-consumer pipeline supports both synchronous and asynchronous
iterables as input and uses asyncio tasks to process items concurrently.
Results are yielded as workers complete, so result order is not guaranteed.

The main public components are :class:`TaskFailedError` and
:func:`run_parallel`. The lower-level :func:`producer`, :func:`worker`, and
:func:`run_all` functions implement the underlying queue-based pipeline.
"""

import asyncio
from collections.abc import (
    AsyncIterable as AsyncIterableABC,
    AsyncIterator,
    Awaitable,
    Callable,
    Iterable,
)
from contextlib import suppress
import functools
import logging
from typing import Concatenate, cast

log = logging.getLogger(__name__)


class sentinel:  # noqa: N801
    """Sentinel type used for internal queue signaling.

    Instances of this class are used to signal workers that no more items
    are available for processing. The class intentionally cannot be
    subclassed.

    The :data:`SENTINEL` instance is used throughout this module instead of
    creating additional sentinel instances.

    Example:
        >>> SENTINEL is sentinel("SENTINEL")
        False
        >>> repr(SENTINEL)
        'SENTINEL'

    """

    __slots__ = ("__name__", "_repr")

    def __init_subclass__(cls) -> None:
        """Prevent subclassing of :class:`sentinel`.

        :raises TypeError: Always raised when an attempt is made to subclass
            :class:`sentinel`.
        """
        raise TypeError("type 'sentinel' is not an acceptable base type")

    def __init__(self, name: str, /, repr: str | None = None) -> None:  # noqa: A002
        """Initialize a sentinel with a name and optional representation.

        :param name: The name assigned to the sentinel.
        :param repr: The string returned by :func:`repr`. If omitted, ``name``
            is used.
        :raises TypeError: If ``name`` is not a string.
        """
        if not isinstance(name, str):
            raise TypeError("sentinel name must be a string")
        self.__name__ = name
        self._repr = repr if repr is not None else name

    def __repr__(self) -> str:
        """Return the configured representation of the sentinel.

        :return: The string representation configured when the sentinel
            was initialized.
        """
        return self._repr


SENTINEL = sentinel("SENTINEL")
type Sentinel = sentinel


class TaskFailedError[T](Exception):
    """Exception wrapper for a task that failed during processing.

    Concurrent processing can produce results out of order, making it
    important to retain the input item associated with a failed operation.
    This exception stores both the original item and the exception raised
    while processing it.

    :param item: The item that was being processed when the failure occurred.
    :param original_exception: The exception raised while processing
        ``item``.

    Example:
        >>> error = TaskFailedError(42, ValueError("invalid item"))
        >>> error.item
        42
        >>> error.original_exception
        ValueError('invalid item')

    """

    def __init__(self, item: T, original_exception: Exception) -> None:
        """Initialize a task failure with its item and original exception.

        :param item: The item that was being processed when the failure
            occurred.
        :param original_exception: The exception raised while processing
            ``item``.
        """
        super().__init__(f"Task failed for item {item}: {original_exception}")
        self.item = item
        self.original_exception = original_exception


async def producer[T](
    items: Iterable[T] | AsyncIterableABC[T],
    input_queue: asyncio.Queue[T | Sentinel],
    num_workers: int,
) -> None:
    """Feed items into the input queue and signal workers when finished.

    The producer accepts either a regular iterable or an asynchronous
    iterable. Items are added to the input queue as they become available.
    Once input processing finishes, one :data:`SENTINEL` is added for each
    worker so that every worker can detect the end of the input stream.

    Sentinel insertion uses :meth:`asyncio.Queue.put_nowait` during cleanup
    so that the producer does not block indefinitely if the queue is full.

    :param items: Iterable or asynchronous iterable containing the items
        to process.
    :param input_queue: Queue into which input items are placed for workers.
    :param num_workers: Number of workers that will consume from
        ``input_queue``. This determines how many sentinels are attempted.
    """
    try:
        if isinstance(items, AsyncIterableABC):
            async for item in items:
                await input_queue.put(item)
        else:
            for item in items:
                await input_queue.put(item)
    finally:
        # Use put_nowait and we must not block here.
        # If the queue is full, skip. Workers don't need more than one
        # sentinel to know it's time to quit.
        for _ in range(num_workers):
            try:
                input_queue.put_nowait(SENTINEL)
            except (asyncio.QueueFull, Exception):
                break


async def worker[T, R](
    worker_fn: Callable[[T], Awaitable[R]],
    input_queue: asyncio.Queue[T | Sentinel],
    result_queue: asyncio.Queue[R | TaskFailedError[T] | Sentinel],
) -> None:
    """Process items from the input queue and place results in the result queue.

    Each worker waits for an item from ``input_queue``, invokes ``worker_fn``
    with that item, and places the resulting value into ``result_queue``.
    Workers terminate when they receive :data:`SENTINEL` or when their task
    is cancelled.

    Exceptions raised by ``worker_fn`` are wrapped in
    :class:`TaskFailedError` and placed into the result queue when possible.
    This allows the remaining items to continue processing instead of
    terminating the complete pipeline because of one failed item.

    :param worker_fn: Asynchronous callable used to process each input item.
    :param input_queue: Queue from which items are consumed.
    :param result_queue: Queue into which successful results and
        :class:`TaskFailedError` instances are placed.
    """
    while True:
        # If the loop is closing, get() might raise CancelledError
        try:
            item = await input_queue.get()
        except asyncio.CancelledError:
            return

        try:
            if item is SENTINEL:
                return

            result = await worker_fn(cast(T, item))
            await result_queue.put(result)
        except Exception as exc:
            # If putting an error fails (queue full), don't deadlock.
            with suppress(asyncio.QueueFull, Exception):
                result_queue.put_nowait(TaskFailedError(cast(T, item), exc))

        finally:
            input_queue.task_done()


async def run_all[T, R](
    items: Iterable[T] | AsyncIterableABC[T],
    worker_fn: Callable[[T], Awaitable[R]],
    input_queue: asyncio.Queue[T | Sentinel],
    result_queue: asyncio.Queue[R | TaskFailedError[T] | Sentinel],
    limit: int,
    *,
    name: str | None = None,
) -> None:
    """Run the producer and workers as a coordinated task group.

    This function creates one producer and ``limit`` worker tasks and manages
    their lifecycle using :class:`asyncio.TaskGroup`. Once all producer and
    worker tasks have completed, a :data:`SENTINEL` is placed in the result
    queue to signal the consumer that no further results will be produced.

    :param items: Iterable or asynchronous iterable containing the items
        to process.
    :param worker_fn: Asynchronous callable used to process each item.
    :param input_queue: Queue used to pass input items from the producer
        to the workers.
    :param result_queue: Queue used to pass worker results to the consumer.
    :param limit: Maximum number of workers to run concurrently.
    :param name: Optional name prefix used when naming the asyncio tasks.
    """
    # Remove the internal .join() and let TaskGroup manage the lifecycle
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(
                producer(items, input_queue, limit),
                name=f"{name}:producer" if name else "producer",
            )
            for i in range(limit):
                tg.create_task(
                    worker(worker_fn, input_queue, result_queue),
                    name=f"{name}:worker-{i + 1}" if name else f"worker-{i + 1}",
                )
    finally:
        # We use put_nowait here. If the result_queue is full,
        # we do not want to deadlock the entire process.
        with suppress(asyncio.QueueFull, Exception):
            result_queue.put_nowait(SENTINEL)


async def run_parallel[T, R, **P](
    items: Iterable[T] | AsyncIterableABC[T],
    worker_fn: Callable[Concatenate[T, P], Awaitable[R]],
    limit: int,
    *worker_args: P.args,
    name: str | None = None,
    **worker_kwargs: P.kwargs,
) -> AsyncIterator[R | TaskFailedError[T]]:
    """Process items concurrently with bounded parallelism.

    ``run_parallel`` implements a producer/worker/consumer pipeline in which
    a single producer feeds items to a bounded input queue and a fixed number
    of workers process those items concurrently. The caller consumes results
    directly by iterating over the returned asynchronous iterator.

    The three pipeline stages operate concurrently. Backpressure propagates
    through the queues: a slow consumer can stall workers, and stalled
    workers can in turn stall the producer.

    Results are yielded in completion order rather than input order. If
    ``worker_fn`` raises an exception for an item, the exception is wrapped
    in :class:`TaskFailedError` and yielded as a result. This allows
    processing of other items to continue after an individual failure.

    The number of concurrently running workers is controlled by ``limit``.
    Input and result queues are bounded to prevent an unbounded number of
    items from accumulating in memory.

    The function is suitable for I/O-bound workloads where workers spend
    significant time awaiting external resources. For CPU-bound work,
    consider using a :class:`concurrent.futures.ProcessPoolExecutor` with
    :meth:`asyncio.loop.run_in_executor`.

    Result ordering is not guaranteed.

    :param items: Iterable or asynchronous iterable containing the items to
        process.
    :param worker_fn: Asynchronous callable invoked as
        ``worker_fn(item, *worker_args, **worker_kwargs)`` for each item.
        The callable must be safe to invoke concurrently from ``limit``
        workers.
    :param limit: Maximum number of workers running concurrently. Must be
        greater than or equal to 1.
    :param worker_args: Additional positional arguments passed to
        ``worker_fn`` for every item.
    :param name: Optional name prefix used when naming the asyncio tasks.
    :param worker_kwargs: Additional keyword arguments passed to
        ``worker_fn`` for every item.
    :raises ValueError: If ``limit`` is less than 1.
    :yields: Successful results in completion order. Failed items are
        yielded as :class:`TaskFailedError` instances instead of their
        original exceptions being raised.

    Example:
        >>> async def double(value: int) -> int:
        ...     return value * 2
        >>> async for result in run_parallel(range(3), double, limit=2):
        ...     print(result)
        0
        2
        4

    A failed item is returned as a :class:`TaskFailedError`:

        >>> async def process(value: int) -> int:
        ...     if value == 2:
        ...         raise ValueError("invalid value")
        ...     return value * 2
        >>> async for result in run_parallel(range(3), process, limit=2):
        ...     if isinstance(result, TaskFailedError):
        ...         print(result.item)
        ...     else:
        ...         print(result)
        0
        2
        1
        4

    """
    if limit <= 0:
        raise ValueError("limit must be >= 1")

    bound_fn = (
        functools.partial(worker_fn, *worker_args, **worker_kwargs)
        if worker_kwargs
        else worker_fn
    )

    input_queue: asyncio.Queue[T | Sentinel] = asyncio.Queue(maxsize=limit * 5)
    result_queue: asyncio.Queue[R | TaskFailedError[T] | Sentinel] = asyncio.Queue(
        maxsize=0
    )

    runner = asyncio.create_task(
        run_all(items, bound_fn, input_queue, result_queue, limit, name=name),
        name=f"{name}:run-all" if name else "run-all",
    )

    try:
        while True:
            result = await result_queue.get()
            if result is SENTINEL:
                break
            yield result  # type: ignore[misc]

    finally:
        if not runner.done():
            runner.cancel()

        with suppress(asyncio.CancelledError, Exception):
            # Always await runner regardless of whether we cancelled it
            # or it finished on its own.
            # This ensures the task is fully cleaned up (no "task was
            # destroyed but it is pending" warnings) and re-raises any unexpected
            # exception from run_all — which we suppress here since we're
            # in a cleanup path and cannot meaningfully recover.
            await runner


if __name__ == "__main__":
    import time

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    async def sample_worker(num: int) -> int:
        """Process a number after simulating an asynchronous I/O operation.

        The example intentionally raises an exception for selected input
        values to demonstrate how :func:`run_parallel` reports failures.

        :param num: Number to process.
        :return: The input number multiplied by two.
        :raises ValueError: When ``num`` is one of the values configured
            to simulate a failure.
        """
        if num in (5, 8):
            log.warning("Simulating failure for item %d", num)
            # HINT: This is the "alternative" implementation.
            # Instead of having a Failure class, we just raise the exception
            # and add the item into the exception as an additional metadata
            raise ValueError("Item 5 is not allowed!", num)
            # Alternative:
            # raise ValueError("Item 5 is not allowed!", {"item": num})

        log.info("Processing item %d", num)
        await asyncio.sleep(0.1)  # Simulate I/O delay
        return num * 2

    # Make process intensive tasks in a executor
    # 1. Define the heavy lifting function (must be at module level for pickle)
    def heavy_cpu_math(item: int) -> int:
        """Perform the CPU-bound calculation used by the example.

        :param item: Input number to calculate.
        :return: The square of ``item``.
        """
        return item * item

    async def main() -> None:
        """Run the concurrency utility examples.

        The first example demonstrates asynchronous I/O-bound processing
        with :func:`run_parallel`. The second demonstrates how the same
        utility can be combined with a
        :class:`concurrent.futures.ProcessPoolExecutor` for CPU-bound work.
        """

        async def generate_items() -> AsyncIterableABC[int]:
            """Generate the integer inputs used by the asynchronous example.

            :yield: Integers from 0 through 9.
            """
            for i in range(10):
                yield i
            # yield from range(10)

        log.info("--- Running process_unordered ---")
        start_time = time.monotonic()
        task_results = (
            res async for res in run_parallel(generate_items(), sample_worker, limit=3)
        )
        end_time = time.monotonic()
        log.info("Finished in %.2f seconds\n", end_time - start_time)

        successful_results = []
        failed_tasks = []
        async for res in task_results:
            if isinstance(res, TaskFailedError):
                failed_tasks.append((res.item, res.original_exception))
            else:
                successful_results.append(res)

        log.info("Successful results (unordered): %s", (successful_results))
        log.info("Caught exceptions: %s", failed_tasks)

        ## -------------------
        log.info("--- Running process executor ---")
        from concurrent.futures import Executor, ProcessPoolExecutor

        # 2. Create the wrapper
        async def cpu_worker_wrapper(
            item: int, executor: Executor | None = None
        ) -> int:
            """Run CPU-bound work through an executor.

            :param item: Input value to process.
            :param executor: Executor used to run the CPU-bound calculation.
                If ``None``, the event loop's default executor is used.
            :return: The result produced by :func:`heavy_cpu_math`.
            """
            loop = asyncio.get_running_loop()
            # Use the passed executor
            return await loop.run_in_executor(executor, heavy_cpu_math, item)

        # 3. Use your existing utility with the executor passed as a kwarg
        items = range(10)
        with ProcessPoolExecutor() as process_pool:

            successful_results = []
            failed_tasks = []
            async for res in run_parallel(
                items, cpu_worker_wrapper, limit=4, executor=process_pool
            ):
                if isinstance(res, TaskFailedError):
                    failed_tasks.append((res.item, res.original_exception))
                else:
                    successful_results.append(res)

        log.info("Successful results (unordered): %s", (successful_results))
        log.info("Caught exceptions: %s", failed_tasks)

    asyncio.run(main())
