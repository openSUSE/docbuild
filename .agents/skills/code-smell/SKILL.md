---
name: code-smell
description: A skill for context-independent code review to find technical flaws and quality issues.
license: GPL-3.0-or-later
compatibility: [opencode, github_copilot, claude]
metadata:
  category: code-quality
  audience: [developers]
---
# Code Smell Skill (Context-Independent)

This skill guides a context-free technical code review to answer: 'Is this well-written code?'

## 1. Code Smells

*   **Duplication (DRY - Don't Repeat Yourself):** Find duplicated code that could be extracted into a function or class.
*   **Complexity:**
    *   **Cyclomatic Complexity:** Are functions too long, with too many nested `if` statements or loops? (Generally, aim for a complexity < 10).
    *   **Cognitive Complexity:** Is the code hard to understand at a glance?
*   **Single Responsibility Principle (SRP):** Does a function or class do more than one thing?
*   **Naming:** Are variable, function, and class names clear, descriptive, and unambiguous?
*   **Dead Code:** Are there any variables, functions, or imports that are unused?

## 2. Logical Flaws and Edge Cases

*   **Error Handling:**
    *   Check for presence of error handling.
    *   Does it catch overly broad exceptions (e.g., `except Exception:`)?
    *   Are there empty `except` blocks that swallow errors silently?
*   **Edge Cases:** How would this code behave with `None`, empty lists, zero, or other boundary values? Are these cases handled gracefully?
*   **Resource Management:** Are files, connections, or other resources properly closed (e.g., using a `with` statement)?

## 3. Security

*   **Input Validation:** Is any input from users, files, or network requests properly validated and sanitized?
*   **Injection Risks:** Is there any possibility of SQL injection, shell injection, or cross-site scripting (XSS)?
*   **Hardcoded Secrets:** Are there any API keys, passwords, or other secrets hardcoded in the source?

## 4. Test Quality

*   **Review the tests, not just the code.**
*   **Do the tests have clear and descriptive names?**
*   **Are the tests too simple?** Do they only test the "happy path"?
*   **Are the tests too complex?** Are they testing too many things at once?
*   **Is mocking used appropriately?** Are the mocks too broad or too specific?

## 5. Output Format

Provide a list of issues, ranked by severity. For each issue, include:

*   **Severity:** 🔴 Critical, 🟠 Major, 🟡 Minor
*   **File and Line Number**
*   **Description of the issue**
*   **Suggestion for a fix**

**Example Issue:**

> **🟠 Major: Broad exception caught**
> *   **File:** `src/docbuild/parser.py:112`
> *   **Issue:** The code catches `except Exception:`, which can hide unexpected errors.
> *   **Suggestion:** Catch a more specific exception, such as `XMLSyntaxError` or `ValueError`.
