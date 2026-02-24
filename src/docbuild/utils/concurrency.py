from abc import ABC, abstractmethod
import asyncio
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
import logging
from typing import TypeVar

T = TypeVar("T")  # Input type
R = TypeVar("R")  # Result type

log = logging.getLogger(__name__)


# HINT(toms): DESIGN Is this really needed?
# This looks like it's a bit overengineered. On the other side, it
# contains the original item of the problem.
#
# Alternative implementation
# Maybe it's enough to add additional args to the exception(s)
# to hold the original item? Something like:
# >>> ValueError("the error message", item)
class Result[R](ABC):
    """Abstract base class for the result of a task."""

    @abstractmethod
    def __init__(self) -> None:
        pass


@dataclass(frozen=True)
class Success[R](Result[R]):
    """Represents a successful task result."""

    result: R


@dataclass(frozen=True)
class Failure[R, T](Result[R]):
    """Represents a failed task result."""

    item: T | None = None
    exception: Exception | None = None


async def map_concurrent(
    items: Iterable[T],
    worker_fn: Callable[[T], Awaitable[R]],
    limit: int,
) -> list[Result[R]]:
    """Apply an async worker function to an iterable of items concurrently.

    This function uses a producer-consumer model with a bounded number of
    concurrent workers managed by an asyncio.TaskGroup. It always waits for
    all tasks to complete.

    :param items: An iterable of items to process.
    :param worker_fn: An async function that processes a single item.
    :param limit: The maximum number of concurrent workers (consumers).
    :return: A list of Success or Failure result objects. The order is not guaranteed.
    """
    queue: asyncio.Queue[T | None] = asyncio.Queue()
    results: list[Result[R]] = []

    async def producer() -> None:
        for item in items:
            await queue.put(item)
        # After producing all items, send "poison pills" to consumers
        for _ in range(limit):
            await queue.put(None)

    async def consumer() -> None:
        while True:
            item = await queue.get()
            if item is None:
                # "Poison pill" received, exit the loop
                break

            try:
                result_val = await worker_fn(item)
                # TODO: What do add here?
                results.append(Success(result=result_val))

            except Exception as e:
                # TODO: What do add here?
                results.append(Failure(item=item, exception=e))

    # Note: asyncio.TaskGroup requires Python 3.11+
    async with asyncio.TaskGroup() as tg:
        tg.create_task(producer())
        for _ in range(limit):
            tg.create_task(consumer())

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

        log.info("--- Running map_concurrent ---")
        start_time = time.monotonic()
        task_results = await map_concurrent(items_to_process, sample_worker, limit=3)
        end_time = time.monotonic()
        log.info("Finished in %.2f seconds\n", end_time - start_time)

        successful_results = []
        failed_tasks = []
        for res in task_results:
            match res:
                case Success(item=i, result=r):
                    successful_results.append((i, res))
                case Failure(item=i, exception=e):
                    failed_tasks.append(res ) # , i, e))
                    print(">>", e.args)

        log.info("Successful results (unordered): %s", (successful_results))
        log.info("Caught exceptions: %s", failed_tasks)

    asyncio.run(main())
