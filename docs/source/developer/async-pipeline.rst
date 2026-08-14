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

       %% Styling
       style Async Pipeline fill:#f9f9f9,stroke:#333,stroke-width:2px
       style Iter fill:#e1f5fe,stroke:#0288d1
       style P1 fill:#fff3e0,stroke:#f57c00
       style P2 fill:#e8f5e9,stroke:#388e3c
       style Output fill:#fce4ec,stroke:#c2185b
