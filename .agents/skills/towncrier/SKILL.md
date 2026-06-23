# Skill - Managing News Fragments (Towncrier)

## Context

This repository uses `towncrier` to generate the changelog. Every pull request that introduces a user-facing change, bugfix or significant internal change must include a news fragment.

## Procedure

1. Identify the issue number associated with your current task.
2. Determine the correct fragment type. Allowed types generally include: `bugfix`, `feature`, `doc`, `removal`, `misc`.
3. Create a new file in the `changelog.d/` directory.
4. The file name must follow the format: `<issue_number>.<type>.rst` (for example, `303.bugfix.rst`).
5. Write a concise, user-facing sentence inside the file explaining the change. Use reStructuredText format.

## Checklist

- [ ] Is the file placed inside the `changelog.d/` directory?
- [ ] Does the file name strictly follow the `<issue_number>.<type>.rst` convention?
- [ ] Is the content written in standard `.rst` format?
- [ ] Is the message clear and focused on user or developer impact?

## Validation

Before concluding the task, run `ls changelog.d/` to verify your file exists and is named correctly. If you have access to the CLI, run a dry-run of towncrier (if available) to ensure the fragment is picked up.
