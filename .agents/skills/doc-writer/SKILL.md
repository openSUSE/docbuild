---
name: doc-writer
description: A skill for ensuring documentation completeness, covering docstring gaps and guide placement.
license: GPL-3.0-or-later
compatibility: [opencode, github_copilot, claude]
metadata:
  category: documentation
  audience: [developers]
---
# Doc Writer Skill

Guides writing and improving project documentation, focusing on docstrings and guides.

## 1. Docstring Completeness

A complete docstring includes these sections (if applicable):

*   A brief, one-line summary of the function/class's purpose.
*   A more detailed explanation of its behavior.
*   **Parameters:** Every parameter must be documented with its type and a description of what it does.
*   **Returns:** The return value must be documented with its type and a description of what it is.
*   **Raises:** Any exceptions that the function is expected to raise must be documented.
*   **Example:** Complex or non-obvious functions should have a usage example.

**Docstring Checklist:**

*   [ ] Is there a one-line summary?
*   [ ] Is there a detailed description?
*   [ ] Are all parameters documented?
*   [ ] Is the return value documented?
*   [ ] Are any potential exceptions documented?
*   [ ] Is there an example (if the function is complex)?

## 2. When to Add Examples

An example is needed if:

*   The function implements a complex algorithm.
*   The function has non-obvious side effects.
*   The function is a decorator or context manager with a specific usage pattern.
*   The function is a core part of the public API that users will interact with frequently.

## 3. Guide Placement

If a change requires a documentation update, decide its placement:

*   **User Guide:** For changes that affect how a user interacts with the application. This includes new features, changes to the CLI, and new configuration options.
*   **Developer Guide:** For changes that affect how a developer works on the project. This includes new internal APIs, changes to the architecture, and new testing procedures.

## 4. Sphinx RST Best Practices

*   Use clear and descriptive section titles.
*   Use `:param:`, `:returns:`, and `:raises:` for documenting function arguments, return values, and exceptions.
*   Use code blocks (``.. code-block:: python``) for examples.
*   Link to other parts of the documentation using `:ref:`.
