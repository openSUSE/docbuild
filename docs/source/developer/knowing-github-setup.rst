.. _know-github-setup:

Knowing GitHub Project Setup
============================

This project uses GitHub for version control and issue tracking.
Additionally, it uses GitHub Actions for different tasks like building the documentation, running tests, and creating a release.


GitHub Actions
--------------

This project uses GitHub Actions extensively. Currently we have
the following Actions:

* :file:`.github/workflows/ci.yml` (CI/Test)

  Runs the automated test suite and verifies code stability across supported Python environments to ensure every change is functional.

* :file:`.github/workflows/codeql-analysis.yml` (CodeQL)

  Performs automated security scanning to identify vulnerabilities and maintain high code quality standards.

* :file:`.github/workflows/gh-pages.yml` (Documentation)

  Builds the Sphinx documentation and deploys it to the gh-pages branch, managing multi-version support and the version switcher.

* :file:`.github/workflows/release.yml` (Release)

  Creates official GitHub Releases, tags the repository, and uploads built assets like wheels when a release branch is merged.

* :file:`".github/workflows/ruff.yml` (Ruff/Linting)

  Enforces consistent coding styles and identifies potential errors through fast linting and formatting checks.

* :file:`.github/dependabot.yml` (Dependabot)

  Automatically checks for and updates dependencies to keep the project secure and up-to-date.

The following diagram illustrates the interrelations between the release workflow and the documentation deployment workflow:

.. mermaid::

   sequenceDiagram
      participant D as Developer
      participant M as main branch
      participant R as release.yml
      participant G as gh-pages.yml

      D->>M: Merge release/0.19.2
      M->>R: Trigger Workflow
      R->>R: Validate & Build
      R->>M: Push Tag (using PAT)
      M->>G: Trigger on Tag
      G->>G: Build Sphinx Docs
      G->>GitHub Pages: Deploy to /v0.19.2/


Issue Templates
---------------

The repository includes issue templates to guide contributors.
These templates assist in providing necessary information when reporting bugs or suggesting features. They help maintain a structured and efficient issue tracking process.

You can find them in the :file:`.github/ISSUE_TEMPLATE` directory of the repository. Currently we distinguish between the following types:

* Bug Report (:file:`bug_report.yml`)

  For reporting bugs or unexpected behavior in the project.

* Feature Request (:file:`feature-request.yml`)

  For suggesting new features or improvements to the project.

* Documentation Issue (:file:`docs-update.yml`)

  For reporting issues related to the documentation, such as errors, omissions, or suggestions for improvement.


Rulesets
--------

Under https://github.com/openSUSE/docbuild/settings/rules we have rulesets to protect the default branch and tags that matches the semantic versioning format.
