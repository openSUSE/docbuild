---
name: create-towncrier-newsfragment
description: Create a valid Towncrier newsfragment for this repository.
---

# Create Towncrier Newsfragment Skill
Use this skill when a user asks to add a changelog entry for a change, PR, or issue.

## Project-specific paths

* Towncrier config: `towncrier.toml`
* Newsfragment directory: `changelog.d/`

## When to use this skill

Use after implementing user-visible changes, such as:

* new features
* bug fixes
* breaking changes
* deprecations/removals
* documentation improvements
* infrastructure changes worth mentioning to users
* refactors that matter for users

Do not use this skill for tiny internal edits that are irrelevant for users.

## Allowed fragment types in this project

From `towncrier.toml`, valid `<TYPE>` values are:

* `breaking`
* `bugfix`
* `deprecation`
* `doc`
* `feature`
* `removal`
* `infra`
* `refactor`

## File naming

Use this format:

`<ISSUE>.<TYPE>.rst`

Rules:

* `<ISSUE>` is usually a GitHub PR or issue number, for example `123`.
* If no issue/PR exists, use a `+` prefix with a short slug, for example:
  `+improve-xml-errors.bugfix.rst`
* `<TYPE>` must be one of the allowed types above.
* Extension must be `.rst`.
* Create files only in `changelog.d/`.

Examples:

* `123.feature.rst`
* `456.bugfix.rst`
* `267.infra.rst`
* `+support-new-lang.doc.rst`

## Content guidelines

Content must be short, user-facing, and in RST format.

Explain the user impact: what changed, why it matters, and any migration notes.

Style guidance:

* Prefer simple past tense or wording with "now".
* Keep one concise paragraph (or a short bullet list for multiple related points).
* Wrap code symbols in double backticks, for example ``docbuild config validate``.
* Avoid deep implementation details unless users must know them.

Good content examples:

* "Improved validation errors for portal config parsing. Error messages now include the failing element path."
* "Added support for prebuilt deliverables in portal examples, so users can document externally built HTML/PDF resources."

Bad content examples:

* "Refactored internal helper function names." (too internal)
* "Changed many things." (not informative)

## Creation workflow

1. Choose the correct fragment type.
2. Choose the filename based on issue/PR number and type.
3. Create the file in `changelog.d/`.
4. Add concise user-focused RST content.
5. Run checks:
   * `uv run --frozen towncrier check`
6. Optionally preview:
   * `uv run --frozen towncrier build --draft`

Example command:

```shell
uv run --frozen towncrier create -c "Added clearer portal validation diagnostics." 321.bugfix.rst
```

## Final checks

* Filename follows `<ISSUE>.<TYPE>.rst`.
* Type is valid for this repository.
* Text is user-facing and concise.
* File exists under `changelog.d/`.
* `uv run --frozen towncrier check` passes.
