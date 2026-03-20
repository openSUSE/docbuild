"""Concurrency utilities using producer-consumer patterns.

This module provides helpers for managing concurrent asyncio tasks with
strict concurrency limits, backpressure handling, and robust exception tracking.

It is designed to handle both I/O-bound tasks (via native asyncio coroutines) and
CPU-bound tasks (via `loop.run_in_executor`) while keeping resource usage deterministic.
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
from typing import Concatenate

log = logging.getLogger(__name__)

#: Sentinel value for internal use when needed (e.g., to signal completion).
SENTINEL = object()


class TaskFailedError[T](Exception):
    """Exception raised when a task fails during processing.

    This wrapper preserves the context of a failure in concurrent processing pipelines.
    Since results may be returned out of order or aggregated later, wrapping the
    exception allows the caller to link a failure back to the specific input item
    that caused it.

    :param item: The item that was being processed.
    :param original_exception: The exception that caused the failure.
    """

    def __init__(self, item: T, original_exception: Exception) -> None:
        super().__init__(f"Task failed for item {item}: {original_exception}")
        self.item = item
        self.original_exception = original_exception


async def producer[T](
    items: Iterable[T] | AsyncIterableABC[T],
    input_queue: asyncio.Queue,
    num_workers: int,
) -> None:
    """Feed items into the input queue, then send one sentinel per worker.

    :param items: An iterable or async iterable of items to be processed.
    :param input_queue: The queue for items to be processed by workers.
    :param num_workers: The number of workers, used to send the correct number of sentinels.
    """
    try:
        if isinstance(items, AsyncIterableABC):
            async for item in items:
                await input_queue.put(item)
        else:
            for item in items:
                await input_queue.put(item)

    except asyncio.CancelledError:
        # We were cancelled — workers are being cancelled too, so there's
        # nobody left to consume sentinels. Don't bother sending them.
        raise

    finally:
        # Normal completion only — workers are still running and need sentinels.
        for _ in range(num_workers):
            await input_queue.put(SENTINEL)


async def worker[T, R](
    worker_fn: Callable[[T], Awaitable[R]],
    input_queue: asyncio.Queue,
    result_queue: asyncio.Queue,
) -> None:
    """Pull items from the input queue, process them, push results out.

    :param worker_fn: The asynchronous function that processes a single item.
    :param input_queue: The queue for items to be processed by workers.
    :param result_queue: The queue for results from the workers.
    """
    while True:
        item = await input_queue.get()
        if item is SENTINEL:
            return
        try:
            result = await worker_fn(item)
            await result_queue.put(result)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            await result_queue.put(TaskFailedError(item, exc))

        finally:
            input_queue.task_done()


async def run_all[T, R](
    items: Iterable[T] | AsyncIterableABC[T],
    worker_fn: Callable[[T], Awaitable[R]],
    input_queue: asyncio.Queue,
    result_queue: asyncio.Queue,
    limit: int,
) -> None:
    """Orchestrate producer + workers, then signal the consumer when done.

    :param items: An iterable or async iterable of items to be processed.
    :param worker_fn: The asynchronous function that processes a single item.
    :param input_queue: The queue for items to be processed by workers.
    :param result_queue: The queue for results from the workers.
    :param limit: The maximum number of concurrent workers.
    """
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(producer(items, input_queue, limit))
            for _ in range(limit):
                tg.create_task(worker(worker_fn, input_queue, result_queue))

    finally:
        await result_queue.put(SENTINEL)


async def run_parallel[T, R, **P](
    items: Iterable[T] | AsyncIterableABC[T],
    worker_fn: Callable[Concatenate[T, P], Awaitable[R]],
    limit: int,
    *worker_args: P.args,
    **worker_kwargs: P.kwargs,
) -> AsyncIterator[R | TaskFailedError[T]]:
    """Process items concurrently with bounded parallelism.

    Uses a producer/worker/consumer pipeline:

    - A single **producer** task feeds items into a bounded input queue.
    - ``limit`` **worker** tasks pull from the input queue, call ``worker_fn``,
      and push results into a bounded result queue.
    - The **caller** consumes results by iterating this async generator.

    All three stages run concurrently. Backpressure propagates naturally:
    a slow consumer stalls workers; stalled workers stall the producer.
    Order of results is NOT guaranteed.

    If ``worker_fn`` raises, the exception is wrapped in
    :class:`TaskFailedError` and yielded rather than re-raised, so one
    failing item does not abort the pipeline.

    Performance characteristics
    ---------------------------
    - **Throughput:** approaches ``limit * per-worker-throughput`` for
      I/O-bound workloads where workers spend most time awaiting external
      resources. CPU-bound work gains little due to the GIL; use
      ``ProcessPoolExecutor`` wrapped in ``asyncio.run_in_executor`` instead.
    - **Startup cost:** O(limit) — one asyncio task per worker, each cheap
      to create (~microseconds).
    - **Memory:** O(limit). Both the input queue (``maxsize=limit * 2``)
      and the result queue (``maxsize=limit * 2``) are bounded. At most
      ``limit`` items are in-flight inside workers at any time, giving a
      total live-item count of roughly ``5 * limit``.
      Note: each item itself may be arbitrarily large; the O(limit) bound
      refers to the *number* of items held in memory, not their byte size.
    - **Latency:** time-to-first-result equals one worker's latency.
      Remaining results stream out as workers complete, with no polling
      delay (sentinel-based signalling, zero busy-wait).
    - **Cancellation:** if the caller abandons the generator (e.g. ``break``
      in an ``async for`` loop), the internal runner task is cancelled and
      all worker tasks are cleaned up promptly via ``TaskGroup``.

    :param items: Iterable or async iterable of items to process.
    :param worker_fn: Async callable invoked as ``worker_fn(item)`` for
        each item. Must be safe to call concurrently from ``limit`` tasks.
    :param limit: Maximum number of concurrent workers. Must be >= 1.
        Higher values increase throughput up to the point where the event
        loop, network, or downstream service becomes the bottleneck.
    :param worker_args: Positional arguments to pass to ``worker_fn``.
    :param worker_kwargs: Keyword arguments to pass to ``worker_fn``.
    :raises ValueError: If ``limit`` is less than 1.
    :yields: Results in completion order (not input order). Failed items
        are yielded as :class:`TaskFailedError` instances rather than
        raising, so the caller can handle partial failures inline.
    """
    if limit <= 0:
        raise ValueError("limit must be >= 1")

    bound_fn = (
        functools.partial(worker_fn, *worker_args, **worker_kwargs) if worker_kwargs else worker_fn
    )

    input_queue: asyncio.Queue[T | object] = asyncio.Queue(maxsize=limit * 2)
    result_queue: asyncio.Queue[R | TaskFailedError[T] | object] = asyncio.Queue(
        maxsize=limit * 2
    )

    runner = asyncio.create_task(
        run_all(items, bound_fn, input_queue, result_queue, limit)
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

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    async def sample_worker(num: int) -> int:
        """Create a simple worker that simulates some I/O-bound work."""
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
        """Simulate a CPU-bound task."""
        return item * item

    async def main() -> None:
        """Run the example."""
        async def generate_items() -> AsyncIterableABC[int]:
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
