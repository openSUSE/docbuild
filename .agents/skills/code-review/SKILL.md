---
name: code-review
description: A skill for context-aware code review to validate implementation against design intent.
license: GPL-3.0-or-later
compatibility: [opencode, github_copilot, claude]
dependencies:
  skills: [testing]

metadata:
  category: code-quality
  audience: [developers]
---
# Code Review Skill (Context-Aware)

This skill guides a context-aware code review to determine if code correctly implements the intended feature.

## 1. Validate Against Design Intent

*   **Read the feature description or task to understand the code's goal.**
*   **Does the code match the design?** If the design specified a particular algorithm, pattern, or library, is the code using it?
*   **Is anything missing?** Does the code implement all aspects of the feature request?
*   **If the code deviates from the design, is the reason valid and documented?**

## 2. Test Coverage and Quality

For all the following items, use the `testing` skill:

*   **Check for test coverage.** Apply the rules in the `testing` skill for a single file and for the whole test suite.
*   **Enforce >95% coverage** for new or modified code.
*   **Coverage must not decrease.** Compare the coverage report with the `main` branch.
*   **Look for untested paths,** especially in error handling and edge cases.
*   **Review the tests themselves.** Are they readable? Do they test the right things? Do they use `pytest` features effectively?

## 3. Code Smells and Best Practices

*   **Readability:** Is the code clear and easy to understand? Are variable names descriptive?
*   **Complexity:** Are there functions or classes that are too long or do too many things (SRP violation)?
*   **Duplication (DRY):** Is there duplicated code that could be extracted into a shared function or class?
*   **YAGNI:** Does the code include any features or flexibility that weren't requested?
*   **Security:** Are there any obvious security vulnerabilities, such as unsanitized input, shell injection, or path traversal issues?

## 4. Output Format

When providing a review, structure the feedback as follows:

1.  **High-Level Summary:** A brief statement on whether the code meets the design intent.
2.  **Test Coverage Analysis:** Note the current coverage percentage, any decrease from `main`, and list any critical untested paths.
3.  **Issues and Suggestions:** Provide a prioritized list of issues (critical to minor), including:
    *   The file and line number.
    *   A clear description of the issue.
    *   A concrete suggestion for how to fix it.

**Example Issue:**

> **🔴 Critical: Unsanitized input used in shell command**
> *   **File:** `src/docbuild/utils/runner.py:42`
> *   **Issue:** The `project_name` parameter is passed directly to a shell command without sanitization.
> *   **Suggestion:** Use `shlex.quote()` to properly escape the `project_name` before including it in the command.
