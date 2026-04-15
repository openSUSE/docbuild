docbuild.utils.concurrency
==========================

.. py:module:: docbuild.utils.concurrency

.. autoapi-nested-parse::

   Concurrency utilities using producer-consumer patterns.

   This module provides helpers for managing concurrent asyncio tasks with
   strict concurrency limits, backpressure handling, and robust exception tracking.

   It is designed to handle both I/O-bound tasks (via native asyncio coroutines) and
   CPU-bound tasks (via `loop.run_in_executor`) while keeping resource usage deterministic.



Exceptions
----------

.. toctree::
   :hidden:

   /reference/_autoapi/docbuild/utils/concurrency/TaskFailedError

.. autoapisummary::

   docbuild.utils.concurrency.TaskFailedError


Functions
---------

.. autoapisummary::

   docbuild.utils.concurrency.producer
   docbuild.utils.concurrency.worker
   docbuild.utils.concurrency.run_all
   docbuild.utils.concurrency.run_parallel
   docbuild.utils.concurrency.sample_worker


Module Contents
---------------

.. py:function:: producer[T](items: collections.abc.Iterable[T] | collections.abc.AsyncIterable[T], input_queue: asyncio.Queue, num_workers: int) -> None
   :async:


   Feed items into the input queue, then send one sentinel per worker.

   :param items: An iterable or async iterable of items to be processed.
   :param input_queue: The queue for items to be processed by workers.
   :param num_workers: The number of workers, used to send the correct number of sentinels.


.. py:function:: worker[T, R](worker_fn: collections.abc.Callable[[T], collections.abc.Awaitable[R]], input_queue: asyncio.Queue, result_queue: asyncio.Queue) -> None
   :async:


   Pull items from the input queue, process them, push results out.

   :param worker_fn: The asynchronous function that processes a single item.
   :param input_queue: The queue for items to be processed by workers.
   :param result_queue: The queue for results from the workers.


.. py:function:: run_all[T, R](items: collections.abc.Iterable[T] | collections.abc.AsyncIterable[T], worker_fn: collections.abc.Callable[[T], collections.abc.Awaitable[R]], input_queue: asyncio.Queue, result_queue: asyncio.Queue, limit: int) -> None
   :async:


   Orchestrate producer + workers, then signal the consumer when done.

   :param items: An iterable or async iterable of items to be processed.
   :param worker_fn: The asynchronous function that processes a single item.
   :param input_queue: The queue for items to be processed by workers.
   :param result_queue: The queue for results from the workers.
   :param limit: The maximum number of concurrent workers.


.. py:function:: run_parallel[T, R, **P](items: collections.abc.Iterable[T] | collections.abc.AsyncIterable[T], worker_fn: collections.abc.Callable[Concatenate[T, P], collections.abc.Awaitable[R]], limit: int, *worker_args: P, **worker_kwargs: P) -> collections.abc.AsyncIterator[R | TaskFailedError[T]]
   :async:


   Process items concurrently with bounded parallelism.

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


.. py:function:: sample_worker(num: int) -> int
   :async:


   Create a simple worker that simulates some I/O-bound work.


