# Contributing to Docbuild

First off, thank you for considering contributing to `docbuild`! It's people like you that make open source such a great community. 

To ensure the project remains sustainable and our maintainers don't burn out, we have a few guidelines. **Please read this document before opening a Pull Request.**

## 🤝 Our Expectations for Contributors

We love helping people learn about open source, Python, and Git. However, reviewing code and fixing broken builds takes significant time. 

When you open a Pull Request (PR), **we expect you to follow through.** 
If you are just looking for a quick "contributed to X" badge and do not intend to respond to review feedback, write tests, or fix failing CI checks, please refrain from opening a PR. Abandoned PRs will be closed.

## 🛠️ Development Setup

`docbuild` uses modern Python tooling. To get your local environment ready:

1. **Clone the repository**:
    ```bash
    git clone [https://github.com/openSUSE/docbuild.git](https://github.com/openSUSE/docbuild.git)
     cd docbuild
    ```

2. **Set up the environment**: Ensure you have your Python virtual environment set up. We rely heavily on `pytest` for testing and `ruff` for formatting and linting.

## 💻 Making Changes

1. **Create a branch**: Always create a new branch for your work. Use a descriptive name (e.g., `feat/live-progress-bar`, `fix/sitemap-urls`).
2. **Write Tests**: If you add a new feature or fix a bug, you must include a test in the `tests/` directory. We strive for high test coverage.
3. **Format and Lint**: Before committing, run the following to ensure your code matches our style guidelines:
    ```bash
    uvx ruff check --fix
    ```
4. **Run the Test Suite**: Ensure all tests pass locally before pushing:
    ```bash
    pytest
    ```

5. **Add a Changelog Entry**: Every significant PR must include a changelog file. Create a file in `changelog.d/` named `<issue_number>.<type>.rst` (e.g., `154.feature.rst` or `123.bugfix.rst`). Write a brief, Sphinx-formatted description of your change.

## 🚀 Submitting a Pull Request

* Fill out the provided Pull Request template completely.
* Link any relevant issues using "Closes #XXX".
* Be patient! Maintainers review PRs in their free time.
* Be prepared to iterate. It is normal for a PR to go through a few rounds of review before it is merged.
