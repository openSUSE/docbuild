# Skill - Managing News Fragments (Towncrier)

## Context

This repository uses `towncrier` to generate the changelog. Every pull request that introduces a user-facing change, bugfix or significant internal change must include a news fragment.

## Procedure

1. Identify the issue number associated with your current task.
2. Determine the correct fragment type. Allowed types are: `breaking`, `bugfix`, `deprecation`, `doc`, `feature`, `refactor`, `removal`, `infra`, `security`.
3. Create a new file in the `changelog.d/` directory.
4. The file name must follow the format: `<issue>.<type>.rst` where `<issue>` is the GitHub pull request or issue number (for example, `303.bugfix.rst`). If there is no issue/PR number, start the file name with `+` and a short slug (for example, `+add-json.feature.rst`).
5. Write a concise, user-facing sentence inside the file explaining the change. Use reStructuredText format.

## Checklist

- [ ] Is the file placed inside the `changelog.d/` directory?
- [ ] Does the file name strictly follow the `<issue>.<type>.rst` convention?
- [ ] Is the content written in standard `.rst` format?
- [ ] Is the message clear and focused on user or developer impact?

## Validation

Before concluding the task, run `towncrier check` to ensure the fragment is valid and will be picked up. Optionally run `towncrier build --draft` to preview the generated changelog output.
