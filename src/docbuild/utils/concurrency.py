
# src/docbuild/utils/concurrency.py
from multiprocessing.sharedctypes import Value
import asyncio
from collections.abc import Awaitable, Callable, Iterable
import logging
from typing import TypeVar

T = TypeVar("T")  # Input type
R = TypeVar("R")  # Result type

log = logging.getLogger(__name__)


async def parallel_process(
    items: Iterable[T],
    worker_fn: Callable[[T], Awaitable[R]],
    *,
    limit: int,
    return_exceptions: bool = False,
    name: str | None = None,
) -> list[R | Exception]:
    """Process a list of items in parallel using a fixed number of workers.

    :param items: An iterable of items to process.
    :param worker_fn: An async function that processes a single item.
    :param limit: The maximum number of concurrent workers.
    :param return_exceptions: If True, exceptions are returned as results
                              instead of raised.
    :param name: Optional name for the task.
    :return: A list of results (unordered unless you track indices).
    """
    queue: asyncio.Queue[T] = asyncio.Queue()
    results: list[R | Exception] = []

    # 1. Populate Queue
    for item in items:
        queue.put_nowait(item)

    # 2. Define Worker
    async def worker() -> None:
        while True:
            try:
                item = await queue.get()
            except asyncio.CancelledError:
                return

            try:
                res = await worker_fn(item)
                results.append(res)

            except Exception as e:
                if return_exceptions:
                    results.append(e)
                else:
                    log.error("Worker failed: %s", e)
                    # Optional: Cancel all other workers here if you want fail-fast
            finally:
                queue.task_done()

    # 3. Start Workers
    workers = [asyncio.create_task(worker(), name=name)
               for _ in range(limit)]

    # 4. Wait & Cleanup
    await queue.join()
    for w in workers:
        w.cancel()
    await asyncio.gather(*workers, return_exceptions=True)

    return results


if __name__ == "__main__":
    import random
    import time

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    async def sample_worker(num: int) -> int:
        """Create a simple worker that simulates some I/O-bound work."""
        log.info("Processing item %d", num)
        x = random.randint(0, 10)
        if x in(1, 5, 6):
            raise ValueError("Oh no! Wrong value!")
        await asyncio.sleep(0.1* x)  # Simulate I/O delay
        return num * 2

    async def main() -> None:
        """Run the example."""
        start_time = time.monotonic()

        log.info("Starting parallel processing with a limit of 3 workers...")
        results = await parallel_process(
            range(20),
            sample_worker,
            limit=5)
        end_time = time.monotonic()

        log.info("Processing finished in %.2f seconds", end_time - start_time)
        log.info("Results (unordered): %s", results)

    print("Starting example...")
    asyncio.run(main())
    print("Example finished.")

