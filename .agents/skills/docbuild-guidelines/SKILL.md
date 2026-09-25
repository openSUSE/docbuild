---
name: docbuild-guidelines
description: What are the coding guidelines for this project?
license: GPL-3.0-or-later
compatibility: [opencode, github_copilot, claude]
metadata:
  category: code-quality
  audience: [developers]
---
# docbuild Coding Guidelines

Core contribution principles for the docbuild project, prioritizing maintainability and clarity.

## 1. Core Philosophy

*   **Surgical and Minimal Changes:** Only touch what is necessary. Do not refactor, reformat, or rename variables outside the core task. The smallest effective change is the best change.
*   **Handling Uncertainty:** If a request is ambiguous or you lack sufficient context, stop and ask for clarification. Do not make assumptions.

## 2. Simplicity First (YAGNI)

*   **You Ain't Gonna Need It.** Do not add features, abstractions, or configurations that are not required by the current task.
*   Avoid single-implementation interfaces or factories for a single product.
*   Prefer simple, readable code over clever one-liners.

## 3. Python and Project Best Practices

*   **Follow PEP 8:** Adhere to the official Python style guide.
*   **Use `ruff`:** Use `ruff format` and `ruff` to enforce and check style automatically.
*   **Use Python 3.12+ features:** Use modern language features and type hints where they improve clarity.
*   **Prefer `pathlib.Path`:** Use `pathlib.Path` for all filesystem paths instead of `os.path`.
*   **Group Imports:** Group imports in the standard order: 1. stdlib, 2. third-party, 3. local application.

## 4. Naming Conventions

*   **Constants:** `SCREAMING_SNAKE_CASE`.
*   **Internal/Private:** Use a leading underscore (`_`) for internal helper functions and methods.
*   **Clarity:** Prefer descriptive, concise names over single-letter variables.

## 5. Control Flow and Error Handling

*   **Guard Clauses:** Use guard clauses to return early and reduce nesting.
*   **Specific Exceptions:** Catch specific exceptions, not the base `Exception`.
*   **Custom Exceptions:** For domain-specific errors, define custom exception classes inheriting from a relevant built-in exception.

## 6. Data Models

*   **Reuse Existing Models:** Before creating a new data structure, check for existing Pydantic models in `src/docbuild/models/`.
*   **`@dataclass` vs. Pydantic:**
    *   Use `@dataclass` for simple, internal data structures from trusted sources.
    *   Use Pydantic for parsing and validating data from external sources, like configuration files.
*   See the `create-pydantic-model` skill for detailed guidance.

## 7. External Processes

When running shell commands, use the project's helpers in this order of preference:
1.  **High-level Git:** Use functions in `docbuild.utils.git` (e.g., `clone_repo`).
2.  **Shell Helpers:** Use async helpers in `docbuild.utils.shell` (e.g., `run_command`).
3.  **Direct `subprocess`:** Only if no project helper fits, use `subprocess.run(..., check=True)`.

## 8. Testing Philosophy

*   **All new code requires tests.**
*   **Test coverage must not decrease** and should aim for >95% on new code.
*   **Tests should be specific and readable.**
*   **Use `pytest.mark.parametrize`** to reduce test boilerplate.
*   See the `pytest-expert` skill for more advanced patterns.

## 9. Documentation

*   **Write Sphinx-style docstrings** for all public modules, classes, and functions.
*   See the `docstrings` skill for formatting details.
