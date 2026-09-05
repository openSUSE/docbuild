---
name: docbuild-guidelines
description: Streamlined coding guidelines for the docbuild project.
license: GPL-3.0-or-later
compatibility: [opencode, github_copilot, claude]
metadata:
  category: code-quality
  audience: [developers]
---
# docbuild Coding Guidelines

Core contribution principles for the docbuild project, prioritizing maintainability and clarity.

## 1. Surgical and Minimal Changes

*   **Only touch what is necessary.** Do not refactor, reformat, or rename variables outside the core task.
*   **The smallest effective change is the best change.**
*   If you notice unrelated dead code or potential improvements, leave a comment or create a separate issue. Do not fix it in the same commit.

## 2. Simplicity First (YAGNI)

*   **You Ain't Gonna Need It.** Do not add features, abstractions, or configurations that are not required by the current task.
*   Avoid single-implementation interfaces or factories for a single product.
*   Prefer simple, readable code over clever one-liners.

## 3. Python and Project Best Practices

*   **Use Python 3.12+ features**, including modern type hints.
*   **Write Sphinx-style docstrings** for all public modules, classes, and functions. Docstrings should be clear, concise, and include examples for complex logic.
*   **Pydantic models** are preferred for structured data.
*   **pathlib.Path** should be used for all filesystem paths.
*   **Follow existing formatting.** The project uses `ruff` to enforce style.

## 4. Testing Philosophy

*   **All new code requires tests.**
*   **Test coverage must not decrease.** New code should aim for >95% coverage.
*   **Tests should be specific and readable.** Use descriptive names for test functions.
*   **Use `pytest.mark.parametrize`** to reduce test boilerplate for similar test cases.

## 5. Handling Uncertainty

*   **If you are unsure, stop and ask.** If a request is ambiguous or you lack sufficient context, ask the user for clarification.
*   **Do not make assumptions.** State what you are unsure about and present options if possible. It is always better to ask than to implement the wrong thing.
