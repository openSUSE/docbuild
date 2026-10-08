Async Pipeline Architecture
===========================

DocBuild uses a pipeline architecture for orchestrating complex, concurrent tasks (like fetching repositories, extracting metadata, and building deliverables).

To achieve this, we use the ``aiostream`` library. It allows us to chain asynchronous generators using a Unix-pipe-like syntax (``|``), automatically handling worker limits, graceful cancellation, and task fan-out.

Pipeline Flow
-------------

The following flowchart illustrates how deliverables stream through the metadata extraction pipeline concurrently:

.. mermaid::

   graph TD
       %% Define the input stream
       Input[/List of Deliverables/] --> Iter[stream.iterate]

       %% Define the pipeline steps
       subgraph Async Pipeline [aiostream Unix-like Pipeline]
           Iter -->|deliverable| P1(pipe.map: update_repositories)
           P1 -->|repo_dir| P2(pipe.map: process_deliverable_wrapper)
       end

       %% Define the output
       P2 -->|success, deliverable| Output[/Failure Collection & Early Exit/]


Implementation & Exception Handling
-----------------------------------

Because ``aiostream`` expects a mapping function to process items cleanly, we wrap our core execution functions to catch exceptions and return structured status tuples (e.g., ``(success_boolean, deliverable)``). This prevents a single failed deliverable from ungracefully crashing the entire pipeline.

Here is a simplified example of how we interact with ``aiostream`` and handle errors:

.. code-block:: python

    from aiostream import stream, pipe

    async def my_task_wrapper(deliverable, *args: object) -> tuple[bool, object]:
        """Wrapper to catch exceptions safely so the pipeline continues."""
        try:
            # Attempt the actual heavy-lifting task
            await process_deliverable(deliverable)
            return True, deliverable
        except Exception as e:
            # Log the error and return a failure state
            log.error(f"Task failed: {e}")
            return False, deliverable

    async def run_pipeline(deliverables):
        # 1. Create the stream
        pipeline = stream.iterate(deliverables) | pipe.map(
            my_task_wrapper, task_limit=8
        )

        failed_items = []

        # 2. Consume the pipeline
        async with pipeline.stream() as streamer:
            async for success, deliverable in streamer:
                if not success:
                    failed_items.append(deliverable)
                    # To "fail fast", we can simply break the loop. 
                    # aiostream automatically safely cancels all pending tasks!
                    # break 

        return failed_items
