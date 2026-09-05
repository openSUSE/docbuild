---
name: documentation
description: A skill for creating and building documentation using Sphinx and custom aliases.
license: GPL-3.0-or-later
compatibility: [opencode, github_copilot, claude]
metadata:
  category: documentation
  audience: [developers]
---
# Skill: Creating and Building Documentation

## Context

This project uses Sphinx with RST source files in `docs/source/`. A custom `makedocs` alias builds the documentation.

## Procedure

1.  **Locate Source:** Navigate to the `docs/source/` directory.

2.  **Edit or Add Content:** Modify existing `.rst` files or create new ones to document features or CLI commands.

3.  **Update Table of Contents:** If you add a new file, ensure it is referenced in the `toctree` of a relevant index file (e.g., `index.rst`).

4.  **Activate Aliases:** Activate custom shell aliases: `source devel/activate-aliases.sh`.

5.  **Build Docs:** Run the custom build command: `makedocs`.

6.  **Verify Output:** The HTML output is generated in `docs/build/html/`. You can open the `index.html` file in that directory to review your changes.

## Checklist

- [ ] Are all your changes located within the `docs/source/` directory?
- [ ] Did you use standard, valid Sphinx-style reStructuredText?
- [ ] If you added a new page, is it included in a `toctree`?
- [ ] Did you build the documentation using the `makedocs` alias?

## Validation

*   A documentation task is not complete if the `makedocs` command produces new errors or warnings (pre-existing warnings can be ignored).
*   The build process must complete with a 0 exit code.
