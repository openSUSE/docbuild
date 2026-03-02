"""Tests for concurrency utilities."""

import asyncio

from docbuild.utils.concurrency import TaskFailedError, run_parallel


async def test_process_unordered_basic():
    """Test basic parallel processing of a list of numbers."""
    async def square(n: int) -> int:
        await asyncio.sleep(0.01)
        return n * n

    items = [1, 2, 3, 4, 5]
    results_gen = run_parallel(items, square, limit=2)

    val_set = set()
    async for r in results_gen:
        assert isinstance(r, int)
        val_set.add(r)

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
