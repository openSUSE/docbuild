---
name: code-style
description: Guidelines for clean, readable, and maintainable Python code.
license: GPL-3.0-or-later
compatibility: [opencode, github_copilot, claude]
metadata:
  category: code-quality
  audience: [developers]
---

# Python Code Style Guide

## When to Use This Skill
Use when writing, refactoring, or reviewing Python code for readability, maintainability, and idiomatic style.

## General Principles

* **Follow PEP 8:** Follow PEP 8, the official Python style guide.
* **Favor Composition Over Inheritance:** Favor composition over inheritance for more flexible and decoupled designs.
* **Target Python Version in `pyproject.toml`:** Use features compatible with the Python version specified in `pyproject.toml`.
* **Use Context Managers (`with`):** Manage resources like files with a `with` statement to ensure they are always closed, even if errors occur.

## Naming

* **Constants:** Use `SCREAMING_SNAKE_CASE` for constants; place shared ones in `constants.py`.
* **Prefer Shorter Names:** Use descriptive, concise variable names (e.g., `num_items`).
* **Leading Underscores:** Use a leading underscore (`_`) to explicitly mark internal/private helper functions and methods.

## Control Flow

* **Prefer `match...case`:** Prefer `match...case` over complex `elif` chains for readability.
* **Use Guard Clauses:** Use guard clauses to return early and reduce nesting. This is ideal for validating inputs or checking preconditions.

    **Example:**
    ```python
    def build_doc(doc):
        if not doc:
            return
        if not doc.is_valid():
            raise InvalidDocError("Document is not valid.")

        # Main logic continues here, un-nested
    ```

## Error Handling

* **Catch Specific Exceptions:** Catch specific exceptions, not the base `Exception`, to avoid hiding bugs.
* **Raise Informative Exceptions:** Raise exceptions with clear context. For domain-specific errors, define custom exception classes.

    **Example:**
    ```python
    class InvalidPortalConfigError(ValueError):
        pass
    raise InvalidPortalConfigError(f"Portal config '{config_path}' is missing a <publication> tag.")
    ```

## Docbuild Project Guidelines

* **Reuse Existing Data Models:** Before creating a new data structure, check for existing Pydantic models in `src/docbuild/models/`. Reusing these models ensures consistency. If you need a new model, see the `create-pydantic-model` skill for guidance.
* **Handling External Processes (Hierarchy):**
    1.  **Git Operations:** For high-level tasks like cloning, use functions in `docbuild.utils.git`.
    2.  **Shell Commands:** If no high-level helper exists, use the async helpers in `docbuild.utils.shell` (e.g., `run_command`).
    3.  **Direct `subprocess`:** Only if no project helper fits, use `subprocess.run(..., check=True)` for synchronous tasks.
* **Prefer `pathlib` for Paths:** Use the `pathlib` module for filesystem paths. Its object-oriented approach is more readable and robust than `os.path`.
    **Example:** `config_path = Path("configs") / "portal.xml"`
* **Choose Between `@dataclass` and Pydantic:**
    * **Use `@dataclass`** for simple, internal data structures where the data source is trusted.
    * **Use Pydantic** for parsing and validation, especially for configuration files from external sources.

## Other Suggestions

* **Use f-strings:** Use f-strings for string formatting.
* **Use Comprehensions:** Use comprehensions and generators for conciseness where readable.
* **Use Immutables:** Use immutable types (`tuple`, `frozenset`) to prevent accidental modification.
* **Use Walrus Operator (`:=`):** Use the walrus operator (`:=`) to simplify logic and avoid repetition where it enhances clarity.
* **Use Type Hints:** Use type hints for clarity and static analysis.
* **Write Docstrings:** Write clear docstrings. See the `docstrings` skill for formatting.
* **Keep Functions Small (SRP):** Functions should be short and follow the Single Responsibility Principle.
* **Automated Linting/Formatting:** Use `ruff format` and `ruff` to enforce style.
* **Wrap Long Lines:** Wrap long lines with parentheses. It's more readable than using a `\` backslash.
* **Group Imports:** Group imports: 1. stdlib, 2. third-party, 3. local. `ruff` can automate this.
