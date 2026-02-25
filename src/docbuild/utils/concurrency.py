"""Concurrency utilities using producer-consumer patterns.

This module provides helpers for managing concurrent asyncio tasks with
strict concurrency limits, backpressure handling, and robust exception tracking.

It is designed to handle both I/O-bound tasks (via native asyncio coroutines) and
CPU-bound tasks (via `loop.run_in_executor`) while keeping resource usage deterministic.
"""

import asyncio
from collections.abc import Awaitable, Callable, Iterable
import logging
from typing import Concatenate

log = logging.getLogger(__name__)


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


async def process_unordered[T, R, **P](
    items: Iterable[T],
    worker_fn: Callable[Concatenate[T, P], Awaitable[R]],
    limit: int,
    *worker_args: P.args,
    **worker_kwargs: P.kwargs,
) -> list[R | TaskFailedError[T]]:
    """Process items concurrently with a worker limit.

    Uses a producer-consumer model via asyncio.TaskGroup.
    Order of results is NOT guaranteed.
    If an exception occurs, it is wrapped in :class:`~docbuild.utils.concurrency.TaskFailedError`.

    :param items: Iterable of items to process.
    :param worker_fn: Async function processing a single item.
        Result signature: ``worker_fn(item, *worker_args, **worker_kwargs)``.
    :param limit: Max concurrent workers.
    :param worker_args: Additional positional arguments passed to ``worker_fn``.
    :param worker_kwargs: Additional keyword arguments passed to ``worker_fn``.
    """
    # Limit queue size to prevent memory explosion if producer is faster than consumers
    queue: asyncio.Queue[T | None] = asyncio.Queue(maxsize=limit * 2)
    results: list[R | TaskFailedError[T]] = []

    async def producer() -> None:
        for item in items:
            await queue.put(item)

    async def consumer() -> None:
        while True:
            item = await queue.get()
            if item is None:
                queue.task_done()
                break

            try:
                result_val = await worker_fn(item, *worker_args, **worker_kwargs)
                results.append(result_val)

            except Exception as e:
                # Wrap the exception in TaskFailedError
                results.append(TaskFailedError(item, e))

            finally:
                queue.task_done()

    async with asyncio.TaskGroup() as tg:
        # Start consumers
        for _ in range(limit):
            tg.create_task(consumer())

        # Push items (blocks if queue is full, providing backpressure)
        await producer()

        # Signal shutdown
        for _ in range(limit):
            await queue.put(None)

        # Wait for all items to be processed
        await queue.join()

    return results


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
        items_to_process = list(range(10))

        log.info("--- Running process_unordered ---")
        start_time = time.monotonic()
        task_results = await process_unordered(items_to_process, sample_worker, limit=3)
        end_time = time.monotonic()
        log.info("Finished in %.2f seconds\n", end_time - start_time)

        successful_results = []
        failed_tasks = []
        for res in task_results:
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
            results = await process_unordered(
                items,
                cpu_worker_wrapper,
                limit=4,
                executor=process_pool
            )

        successful_results = []
        failed_tasks = []
        for res in results:
            if isinstance(res, TaskFailedError):
                failed_tasks.append((res.item, res.original_exception))
            else:
                successful_results.append(res)

        log.info("Successful results (unordered): %s", (successful_results))
        log.info("Caught exceptions: %s", failed_tasks)

    asyncio.run(main())
