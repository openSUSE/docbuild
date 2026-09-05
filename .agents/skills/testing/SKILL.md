---
name: testing
description: A skill for running and interpreting tests in the repository using pytest and custom aliases.
license: GPL-3.0-or-later
compatibility: [opencode, github_copilot, claude]
metadata:
  category: testing
  audience: [developers]
---
# Skill: Running and Interpreting Tests

## Context

This repo uses `pytest` via a custom `upytest` alias. Tests are in the `tests/` directory.

## Procedure

1.  **Activate Aliases:** Activate development aliases: `source devel/activate-aliases.sh`.

2.  **Run Tests:** Use the `upytest` command:
    *   **All Tests:** `upytest`
    *   **Specific File:** `upytest tests/path/to/test_file.py`
    *   **Specific Function:** `upytest tests/path/to/test_file.py::test_function_name`

3.  **Use Options:** Add flags to modify the run:
    *   `-v`: Increase verbosity to get full diffs on failures.
    *   `-q`: Quieter output.
    *   `-x`: Stop after the first failure.
    *   `--lf`: Rerun only the last failed tests.
    *   `--no-cov`: Disable coverage for a faster run (e.g., when debugging a single test).

4.  **Analyze Output:** If tests fail, read the traceback carefully. Look for assertion errors, missing mocks, or formatting mismatches (like unexpected newlines in rich console outputs).

## Checklist

- [ ] Did you use `upytest` instead of `pytest`?
- [ ] If tests failed, did you trace the failure back to the exact line in the test or source code?
- [ ] Did you handle special formatting or newlines if testing rich CLI output?
- [ ] **CRITICAL:** Ignore "Required test coverage... not reached" failures on targeted runs, as this is expected.

## Validation

* A task is not considered complete until `upytest` returns a 0 exit code on the full suite.
* Always run tests after making a code change. Do not assume the code works.
* Keep total test coverage above 95%.
