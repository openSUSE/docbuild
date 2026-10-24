---
name: docstrings
description: How do I write docstrings for my Python code?
license: GPL-3.0-or-later
compatibility: [opencode, github_copilot, claude]
metadata:
  category: documentation
  audience: [developers]
---
# Docstring Formatting Skill

Write complete Sphinx reStructuredText (RST) Python docstrings wrapped at 80 characters.

## Procedure: Writing a Docstring

1. **One-Line Summary:** Complete sentence summarizing the purpose.
2. **Blank Line:** Follow the summary with a single blank line.
3. **Detailed Explanation (Optional):** Paragraphs detailing behavior or design rationale.
4. **Click Commands (`\f`):** For Click (sub-)commands only, insert `\f` on its own line before developer RST fields to truncate `--help`. Use standard `"""` (not `r"""`) and add `# noqa: D301` to the closing quotes.
5. **RST Sections:** Document fields with types and descriptions:
   * `:param name: (type) Description.`
   * `:returns: (type) Description.`
   * `:raises ExceptionName: Explanation.`
6. **Usage Example (Optional):** In a `.. code-block:: python` directive.
7. **Line Width:** Keep all lines under 80 characters (including indentation).

```python
"""User-facing CLI description.

\f

:param ctx: Developer-only documentation.
"""  # noqa: D301
```

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
*   [ ] For Click (sub-)commands only: is `\f` used to separate user help from developer RST fields, followed by `"""  # noqa: D301`?
