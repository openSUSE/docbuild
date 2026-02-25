"""Concurrency utilities."""

import asyncio
from collections.abc import Awaitable, Callable, Iterable
import logging
from typing import TypeVar

T = TypeVar("T")  # Input type
R = TypeVar("R")  # Result type

log = logging.getLogger(__name__)


async def process_unordered(
    items: Iterable[T],
    worker_fn: Callable[[T], Awaitable[R]],
    limit: int,
) -> list[R | Exception]:
    """Process items concurrently with a worker limit.

    Uses a producer-consumer model via asyncio.TaskGroup.
    Order of results is NOT guaranteed.
    If an exception occurs, the exception object is returned in the list.
    The original item is attached to the exception as `e.item`.

    :param items: Iterable of items to process.
    :param worker_fn: Async function processing a single item.
    :param limit: Max concurrent workers.
    """
    # Limit queue size to prevent memory explosion if producer is faster than consumers
    queue: asyncio.Queue[T | None] = asyncio.Queue(maxsize=limit * 2)
    results: list[R | Exception] = []

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
                result_val = await worker_fn(item)
                results.append(result_val)

            except Exception as e:
                # Attach the item to the exception for tracking
                e.item = item  # type: ignore[attr-defined]
                results.append(e)

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
            match res:
                case Exception(item=i):
                    failed_tasks.append((i, res))
                case _:
                    # Order lost, but we have results
                    successful_results.append(res)

        log.info("Successful results (unordered): %s", (successful_results))
        log.info("Caught exceptions: %s", failed_tasks)

    asyncio.run(main())
