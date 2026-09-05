---
name: pytest-expert
description: A skill for advanced pytest usage, covering parametrization, fixtures, mocking, and coverage analysis.
license: GPL-3.0-or-later
compatibility: [opencode, github_copilot, claude]
metadata:
  category: testing
  audience: [developers]
---
# Pytest Expert Skill

Guidelines for writing clean, efficient, and maintainable tests with advanced `pytest` features.

## 1. Parametrization (`@pytest.mark.parametrize`)

*   **Use parametrization to reduce boilerplate.** Combine tests that use different inputs/outputs for the same logic into a single parametrized test.
*   **Give clear names to your test cases** using the `ids` parameter. This makes test reports much easier to read.

**Example:**

```python
# BAD: Duplicated test logic
def test_is_even_2():
    assert is_even(2)

def test_is_even_4():
    assert is_even(4)

# GOOD: Parametrized test
@pytest.mark.parametrize(
    "number, expected",
    [(2, True), (3, False), (0, True), (-1, False)],
    ids=["even", "odd", "zero", "negative_odd"],
)
def test_is_even(number, expected):
    assert is_even(number) == expected
```

## 2. Fixtures

*   **Use fixtures for setup and teardown.** Use fixtures to provide data, services, or other resources to tests.
*   **Choose the right scope.** Use `scope="session"` for resources that can be shared across all tests, `scope="module"` for module-level resources, and the default `scope="function"` for resources that need to be reset for each test.
*   **Use `yield`** in fixtures to perform teardown actions after the test has run.

**Example:**

```python
@pytest.fixture
def temp_file():
    # Setup: create a temporary file
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("hello")
        filepath = f.name

    yield filepath

    # Teardown: clean up the file
    os.remove(filepath)

def test_read_file(temp_file):
    content = read_file_content(temp_file)
    assert content == "hello"
```

## 3. Mocking

*   **Use `pytest-mock`** (via the `mocker` fixture) for all mocking.
*   **Be specific.** Mock the smallest possible unit. Instead of mocking `requests.get`, mock the specific function in your own code that calls it.
*   **Don't mock everything.** Only mock external services, functions that are slow, or functions with non-deterministic behavior (like `datetime.now()`). Do not mock your own application's internal logic.

## 4. Coverage Analysis

*   **Run tests with `pytest --cov=src`** to generate a coverage report.
*   **Review the `term-missing` report** to see exactly which lines of code are not being tested.
*   **Aim for >95% coverage,** but don't stop there. 100% coverage is not a guarantee of good tests. Make sure the tests are actually asserting something meaningful.
*   **Pay special attention to missing coverage in error handling** (`except` blocks) and complex conditional logic (`if`/`elif`/`else`).
