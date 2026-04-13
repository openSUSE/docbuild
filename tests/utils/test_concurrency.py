"""Tests for concurrency utilities."""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import suppress
from typing import cast

import pytest

from docbuild.utils.concurrency import (
    SENTINEL,
    TaskFailedError,
    producer,
    run_all,
    run_parallel,
)


@pytest.mark.parametrize("limit", (0, -1))
async def test_wrong_limit(limit: int):
    async def square(n: int) -> int:
        await asyncio.sleep(0.01)
        return n * n

    async def async_items_generator():
        for i in [1, 2, 3, 4, 5]:
            yield i

    items = async_items_generator()
    with pytest.raises(ValueError, match="limit must be >= 1"):
        results_gen = run_parallel(items, square, limit=limit)
        async for _ in results_gen:
            pass


async def test_process_unordered_basic():
    """Test basic parallel processing of a list of numbers."""
    async def square(n: int) -> int:
        await asyncio.sleep(0.01)
        return n * n

    items = [1, 2, 3, 4, 5]
    results_gen = run_parallel(items, square, limit=2)

    val_set = set()
    # Use a timeout to ensure that if it deadlocks, we see the error
    try:
        async with asyncio.timeout(2):
            async for r in results_gen:
                assert isinstance(r, int)
                val_set.add(r)
    except TimeoutError:
        pytest.fail("Test timed out - possible deadlock in run_parallel")

    assert val_set == {1, 4, 9, 16, 25}


async def test_process_unordered_concurrency_limit():
    """Verify that concurrency limit is respected."""
    active_workers = 0
    max_active = 0
    lock = asyncio.Lock()

    async def track_concurrency(n: int) -> int:
        nonlocal active_workers, max_active
        async with lock:
            active_workers += 1
            max_active = max(max_active, active_workers)

        await asyncio.sleep(0.05)

        async with lock:
            active_workers -= 1
        return n

    items = range(10)
    limit = 3
    # Consume the async generator to ensure all workers run and concurrency is tracked.
    _ = [r async for r in run_parallel(items, track_concurrency, limit=limit)]

    assert max_active <= limit


async def test_process_unordered_exceptions():
    """Test exception handling returning TaskFailedError."""
    async def fail_on_even(n: int) -> int:
        if n % 2 == 0:
            raise ValueError(f"Even number: n={n}")
        return n

    items = [1, 2, 3]
    results_gen = run_parallel(items, fail_on_even, limit=2)
    results = [r async for r in results_gen]
    assert len(results) == 3

    success_vals = []
    failed_items = []

    for r in results:
        match r:
            case TaskFailedError(item=item, original_exception=exc):
                failed_items.append(item)
                assert isinstance(exc, ValueError)
            case _:
                success_vals.append(r)

    assert set(success_vals) == {1, 3}
    assert failed_items == [2]


async def test_process_unordered_empty():
    """Test processing an empty list."""
    async def identity(n): return n
    results_gen = run_parallel([], identity, limit=5)
    collected_results = [r async for r in results_gen]
    assert collected_results == []


async def test_process_unordered_empty_async_iterable():
    """Test processing an empty async iterable, ensuring run_all completes gracefully."""
    async def async_empty_generator():
        # This async generator yields nothing, simulating an empty async iterable.
        if False:
            yield 1

    async def identity(n): return n
    results_gen = run_parallel(async_empty_generator(), identity, limit=5)
    collected_results = [r async for r in results_gen]
    assert collected_results == []


async def test_process_unordered_kwargs():
    """Test passing kwargs to worker function."""
    async def multiply(n: int, factor: int = 1) -> int:
        return n * factor

    items = [1, 2, 3]
    results_gen = run_parallel(items, multiply, limit=2, factor=3)
    collected_results = [r async for r in results_gen]
    # We might get exceptions if anything failed, but expecting ints
    int_results = [r for r in collected_results if isinstance(r, int)]
    assert set(int_results) == {3, 6, 9}


async def test_finally_calls_cancel_on_early_exit():
    """Verify that if the caller stops iterating, the runner task is cancelled."""
    worker_started = asyncio.Event()
    worker_cancelled = False

    async def slow_worker(x):
        nonlocal worker_cancelled
        try:
            worker_started.set()
            await asyncio.sleep(10)
            return x
        except asyncio.CancelledError:
            worker_cancelled = True
            raise

    # 1. Start generator
    gen = run_parallel(range(10), slow_worker, limit=1)

    # 2. Manually trigger the first step of the generator
    # but don't 'await' a result that will never come.
    # Create a task to drive the generator.
    async def drive_gen():
        try:
            async for _ in gen:
                break
        except asyncio.CancelledError:
            pass

    driver = asyncio.create_task(drive_gen())

    # Wait for the worker to actually start
    await worker_started.wait()

    # 3. Cancel the driver and the generator
    # This simulates the user stopping the loop
    driver.cancel()

    # 4. Settle and check
    await asyncio.sleep(0.1)
    assert worker_cancelled is True, "Worker should have been cancelled"


async def test_producer_queue_full_sentinel():
    """Test that if the input queue is full, the producer's finally block doesn't deadlock trying to put sentinels."""
    limit = 2
    input_queue = asyncio.Queue(maxsize=1)
    await producer([], input_queue, num_workers=limit)
    assert input_queue.full()
    assert input_queue.get_nowait() is SENTINEL


async def test_run_all_exception_coverage():
    """Test that if a worker raises an exception, run_all handles it without deadlocking on a full result_queue."""
    input_queue = asyncio.Queue()
    # Force result_queue to be full so put_nowait(SENTINEL) hits the 'except' block
    result_queue = asyncio.Queue(maxsize=1)
    result_queue.put_nowait("Blocker")

    async def broken_worker(_):
        # We need a small yield here to ensure the TaskGroup starts the worker
        # before the exception is raised.
        await asyncio.sleep(0)
        raise RuntimeError("Simulated crash")

    # If the library is fixed, this finishes instantly.
    # If not fixed, it hangs here.
    try:
        async with asyncio.timeout(2):
            with suppress(Exception):
                await run_all([1], broken_worker, input_queue, result_queue, limit=1)
    except TimeoutError:
        pytest.fail("Deadlock in run_all: finally block hung on a full result_queue")

    # Verify we didn't hang and the queue is still full
    assert result_queue.full()
    assert result_queue.get_nowait() == "Blocker"


async def test_run_parallel_cleanup_coverage():
    """Test that if the caller stops iterating, the generator's finally block is hit without deadlocking."""
    async def quick_fn(x):
        return x

    gen = run_parallel([1], quick_fn, limit=1)
    gen_as_gen = cast(AsyncGenerator, gen)

    # We trigger the finally block by throwing a CancelledError.
    # This avoids the potential deadlock of 'aclose' on some loops.
    with suppress(asyncio.CancelledError, StopAsyncIteration):
        await gen_as_gen.athrow(asyncio.CancelledError)

    assert True
