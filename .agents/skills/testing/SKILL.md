# Skill - Running and Interpreting Tests

## Context

This repository uses `pytest` for testing, wrapped in a custom alias script to ensure the environment is correctly configured before tests run. 

## Procedure

1. Before running tests, ensure the development aliases are active in your session.
2. Run the test suite using the project-specific alias `upytest` (instead of standard `pytest`).
3. If running a specific test file, append the path and **always use the verbose flag (`-v`)** to get elaborate output and full string diffs: `upytest -v tests/path/to/test.py`.
4. Analyze the output. If tests fail, read the traceback carefully, specifically looking for assertion errors, missing mocks, or formatting mismatches (like unexpected newline characters in rich console outputs).

## Checklist

- [ ] Did you use `upytest` instead of standard `pytest`?
- [ ] If tests failed, did you trace the failure back to the exact line in the test file or source code?
- [ ] Did you strip or handle terminal formatting or newlines in string assertions if testing rich CLI output?
- [ ] **CRITICAL**: If you ran `upytest` on a *specific* test file, did you ignore the inevitable coverage threshold failure (< 90%)? (This is normal behavior for targeted runs and is not an actual test error).

## Validation

Always execute the test command after making a code change. Do not assume the code works. If tests fail, automatically attempt a fix based on the traceback before asking the user for help. A task is not complete until `upytest` returns a 0 exit code.
