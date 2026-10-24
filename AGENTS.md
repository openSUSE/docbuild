# Docbuild Project

This document outlines key information about the `docbuild` project to assist AI agents and developers.

## Purpose of this Project (Docbuild)

Docbuild builds documentation from DocBook 5/ASCIIDoc, manages XML configs, clones repos, runs `daps`, handles metadata and syncing deliverables.

## Agentic Workflow

This project uses a sophisticated agentic workflow to assist with development. For a detailed explanation of the agents and how to use them, please see the **[Agentic Workflow Guide](docs/source/developer/agentic-workflow.rst)**.

### Quick Command Reference

*   `@docbuild <task>`: The primary orchestrator agent.
*   `@code-reviewer <path>`: Context-aware code review.
*   `@test-engineer <path>`: Testing and coverage analysis.
*   `@doc-writer <path>`: Documentation and docstring completion.
*   `@design-reviewer <path>`: Architecture and design review.
*   `@pr-reviewer <pr_url>`: Context-independent PR review.

## Repository Facts

*   **Python Version:** >= 3.12
*   **Package Manager:** `uv` (Astral)
*   **Key Directories:**
    *   `src/`: Source code
    *   `tests/`: Test suite (pytest)
    *   `.github/workflows/`: CI/CD configurations
*   **CLI Entry Point:** `docbuild` (file `src/docbuild/__main__.py`)
*   **Documentation:** https://opensuse.github.io/docbuild/

## Setup

1.  Create a virtual environment with `uv venv`
2.  Install dependencies: `uv sync --frozen --no-sync`

## Testing with `uv`

To run tests in this environment, use the following commands:

*   **Run complete test suite:**

    ```bash
    uv run --frozen pytest
    ```

*   **Run single test file:**

    ```bash
    uv run --frozen pytest tests/path/to/test_file.py
    ```
