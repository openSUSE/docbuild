---
name: doc-writer
description: Write and structure the User, Developer, and Reference guides (Sphinx RST prose). Defines guide placement and the project's prose writing style, including procedures as numbered steps. For Python docstrings, use the `docstrings` skill instead.
license: GPL-3.0-or-later
compatibility: [opencode, github_copilot, claude]
metadata:
  category: documentation
  audience: [developers]
---
# Doc Writer Skill

Authority for **narrative documentation** in `docs/source/` (the User,
Developer, and Reference guides). Covers *where* content goes and *how* to
write it.

> **Scope boundary.** This skill does **not** cover Python docstrings. For
> `:param:`/`:returns:`/`:raises:` and in-code API documentation, use the
> **`docstrings`** skill. If a task is only about docstrings, stop and switch.

## 1. Guide placement

Decide which guide a change belongs to before writing:

* **User Guide** (`docs/source/user/`): how someone *uses* docbuild. New
  features, CLI commands/options, configuration, and end-to-end procedures.
  Written for readers who run `docbuild`, not those who hack on it.
* **Developer Guide** (`docs/source/developer/`): how someone *works on*
  docbuild. Architecture, internal APIs, how-to procedures for contributors,
  schema editing, testing, and release workflow. The `developer/howto/`
  subtree holds task-oriented procedures.
* **Reference Guide** (`docs/source/reference/`): generated API/CLI/env
  reference (autoapi, CLI docs, env-toml). Prefer improving docstrings and
  source annotations over hand-editing here; only add hand-written reference
  prose when generation can't express it.

If a change is user-facing *and* affects contributors, update both the User
and Developer guides rather than cramming everything into one.

## 2. Prose writing style

* **Imperative, second person.** "Run the command", "Set the variable" — not
  "The user should run" or "We run".
* **Present tense**, active voice. Short sentences, one idea each.
* **One sentence per line** in RST source where practical (cleaner diffs).
* **Define terms once**, link afterward. Add new terms to `glossary.rst` and
  reference them with `:term:`.
* **Say why, not just what**, when the reason isn't obvious.

## 3. Procedures = numbered steps

Any task with an order of operations is a procedure. Write it as an
auto-numbered RST list, not a paragraph:

* Use `#.` for auto-numbered steps (keeps renumbering free).
* **One action per step.** If a step has two verbs, split it.
* Start each step with an imperative verb.
* Put commands in a `.. code-block:: console` (or `python`) directly under
  the step, indented, ideally with a `:caption:`.
* Introduce the procedure with a one-line lead-in ending in a colon.

**Exception: single-step tasks.** If the task is simple enough to be a single
step, don't wrap it in a one-item list. Describe it in a short paragraph
instead (with a code block if a command is involved).

```rst
To migrate an existing config, do the following:

#. Copy the stitchfile to your machine:

   .. code-block:: console

      scp server:/tmp/docserv-stitch.xml .

#. Run the migration wrapper:

   .. code-block:: console

      tools/migrate-config.sh docserv-stitch.xml
```

## 4. RST conventions

* **Cross-references**, never bare names or paths:
  * `:ref:` for labelled sections, `:doc:` for whole pages.
  * `:class:`, `:func:`, `:mod:`, `:meth:` for Python objects.
  * `:file:` for paths, `:command:` for executables.
* **Code blocks** use `.. code-block:: <lang>` with a `:caption:` when the
  block benefits from a title. Use `console` for shell sessions, `python`,
  `xml`, `rnc`, `toml` as appropriate.
* **Admonitions** (`.. note::`, `.. warning::`, `.. tip::`) for asides — keep
  them short and rare; overuse dilutes them.
* **Section titles**: sentence case, descriptive, underlined consistently with
  the surrounding file.
* Add a `.. _label:` target above sections you expect to link to.

## 5. Checklist

* [ ] Correct guide chosen (User / Developer / Reference)?
* [ ] Ordered tasks written as `#.` step procedures, one action per step?
* [ ] Imperative, active, present-tense prose?
* [ ] Names/paths/commands wrapped in the right roles (`:class:`, `:file:`, …)?
* [ ] Code blocks use the right language and a `:caption:` where useful?
* [ ] Cross-references resolve (`:ref:` targets exist)?
* [ ] Docstring-only work delegated to the `docstrings` skill?
