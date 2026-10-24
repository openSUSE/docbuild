<!-- Copilot instructions for working on the docbuild repository -->
# Copilot / AI agent quick instructions

## Purpose
- Help an AI coding assistant become productive quickly in this repository: explain the project's layout, common developer workflows, important conventions, and concrete file examples to inspect.

## Quick overview
- This is a Python project using the `src/` layout (see `pyproject.toml` -> `package-dir = {"" = "src"}`).
- Primary package: `src/docbuild` (CLI entrypoint: `docbuild` defined in `pyproject.toml`).
- Key resources: `pyproject.toml`, `src/`, `tests/`, and `docs/`.

## Architecture & intent
- The codebase is a CLI-driven documentation build tool — lightweight, single-process Python application.
- Packaging is managed with setuptools (see `[build-system]` and `[project]` in `pyproject.toml`). Version is dynamic (read from `docbuild.__about__.__version__`).

## Concrete developer workflows
- Create a development environment:

  uv sync --group devel

- Run tests:

  uv run --frozen pytest -q

- Run the CLI locally (module entrypoint):

  uv run --frozen docbuild --help


## Project-specific conventions and patterns
- `src/` layout: All importable code lives under `src/`. Use package paths like `docbuild.utils.contextmgr` when searching.
- Prefer `pathlib.Path` for filesystem paths and `dataclasses`/`pydantic` for structured data.
- Async support: some utilities expose both sync and async context managers (see `src/docbuild/utils/contextmgr.py` for patterns like `PersistentOnErrorTemporaryDirectory` and `make_timer`). When modifying such utilities, preserve both sync and async entry/exit behavior.
- Atomic file writes: the project favors safe write patterns (atomic tempfile -> replace -> fsync) — maintain these patterns when editing file-writing code (see `edit_json` in `contextmgr.py`).

## Tooling & formatting
- Development environment managed with `uv` (see `uv.toml`).
- The project provides development groups in `pyproject.toml`. Formatting and linting tools used include `docformatter` and `ruff`. 
- Respect existing formatting rules and run the same tools the repo uses.
- Try to make minimal, focused changes when editing code to avoid large diffs.

## CI, packaging & release notes
- CI test workflow: `.github/workflows/ci.yml`
- Changelog generation uses `towncrier` (see `towncrier.toml` / `pyproject.toml` changelog group). Follow the existing changelog fragment pattern in `changelog.d/`.

## Integration & extension points
- External dependencies listed in `pyproject.toml` (Jinja2, lxml, pydantic, rich). Avoid adding runtime deps unless necessary.


## Files to inspect for context (start here)
- `pyproject.toml` — packaging, deps, dev groups
- `src/docbuild/cli` — CLI command implementations
- `src/docbuild/config` — configuration loading and management
- `src/docbuild/__main__.py` and `src/docbuild` — CLI entry and core library
- `src/docbuild/models` — Pydantic models for structured data
- `changelog.d/` and `towncrier.toml` — release note workflow

## When you're unsure
- Prefer reading nearby tests in `tests/` to confirm expected behavior before making changes.
- If changing I/O semantics (file writes, fsyncs, temp dirs), run unit tests and validate behavior on POSIX systems.

## What to ask the human reviewer
- Any missing implicit conventions I should follow (e.g., preferred test naming, CI guardrails, versioning policy)?
- Should I prefer certain formatters or linters (the repo includes `docformatter` and `ruff`?

End of instructions
