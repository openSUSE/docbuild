---
name: docstrings
description: A skill for writing complete and correctly formatted Python docstrings in RST/Sphinx style.
license: GPL-3.0-or-later
compatibility: [opencode, github_copilot, claude]
metadata:
  category: documentation
  audience: [developers]
---
# Docstring Formatting Skill

This skill provides a detailed procedure for writing a complete and syntactically correct Python docstring using reStructuredText (RST) for Sphinx.

## Procedure: Writing a Docstring

A complete docstring must be formatted according to these rules:

1.  **One-Line Summary:** Start with a brief, one-line summary of the function/class's purpose. This line should be a complete sentence.
2.  **Blank Line:** The summary line must be followed by a single blank line.
3.  **Detailed Explanation (Optional):** If the function's purpose is not obvious from the summary, add more detailed paragraphs explaining its behavior, algorithms, or design rationale.
4.  **RST Sections:** Use the following RST field lists to document parameters, return values, and exceptions. Each entry should include the type and a clear description.
    *   `:param name: (type) Description of the parameter.`
    *   `:returns: (type) Description of the return value.`
    *   `:raises ExceptionName: Explanation of when the exception is raised.`
5.  **Usage Example:** If the function is complex or part of a public API, include a usage example within a `.. code-block:: python` directive.
6.  **Line Width:** All lines within the docstring, including code examples, must be wrapped to keep the total line length (including the indentation of the docstring) under 80 characters.

## Validation Checklist

Before finishing, ensure the docstring meets these criteria:
*   [ ] Does it start with a one-line summary?
*   [ ] Is the summary followed by a blank line?
*   [ ] Are all parameters documented using the correct `:param:` syntax?
*   [ ] Is the return value documented using the correct `:returns:` syntax?
*   [ ] Are potential exceptions documented using `:raises:`?
*   [ ] Is the RST syntax valid and clean?
*   [ ] Is there a code example if one is needed?
*   [ ] Does the docstring respect the 80-character line width limit?
