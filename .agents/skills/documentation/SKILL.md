# Skill - Creating and Building Documentation

## Context

This project uses Sphinx for documentation. The source files are written in reStructuredText (.rst) and the configuration is handled via `conf.py`. 

**Note on Structure**: The documentation is separated into different guides (for example, user, developer, etc.). When reading or updating documentation, always ensure you are navigating and modifying the correct guide for the target audience.

## Procedure

1. Locate the documentation source files in `docs/source/`.
2. Edit or add `.rst` files as needed to document new features or CLI commands.
3. If adding a new file, ensure it is referenced in the `toctree` of an existing index file.
4. Ensure the custom aliases are active (`source devel/activate-aliases.sh`).
5. Build the documentation by running the custom alias: `makedocs`.
6. The HTML output is generated and placed in the appropriate build output directory (usually `docs/build/html/`).

## Checklist

- [ ] Are changes placed inside `docs/source/`?
- [ ] Did you use standard Sphinx-style reStructuredText?
- [ ] Did you build the docs using the `makedocs` alias?
- [ ] Did the build complete without Sphinx errors? (**Note**: It is safe to ignore pre-existing warnings).

## Validation

Always run `makedocs` after modifying `.rst` files or docstrings. Do not consider a documentation task complete if the Sphinx build emits warnings or errors.
