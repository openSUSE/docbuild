.. _know-github-setup:

Knowing GitHub Project Setup
============================

This project uses GitHub for version control and issue tracking.
Additionally, it uses GitHub Actions for different tasks like building the documentation, running tests, and creating a release.


GitHub Actions
--------------

* Testing (:file:`.github/workflows/ci.yml`):
  Runs the test suite on every push and pull request to the main branch.
  It uses the `pytest` framework to execute tests.

* Documentation (:file:`.github/workflows/gh-pages.yml`):
  Builds the documentation and deploys it to the `gh-pages` branch.
  This is triggered on every push to the main branch and on pull requests that target the main. Furthermore it is only triggered if the workflow file itself is changed or anything inside the `docs/` directory.
  The documentation is available at |gh_repo|.

* Release (:file:`.github/workflows/release.yml`):
  Create a new release when a tag is pushed to the repository.
  It is triggered by a tag in the format `MAJOR.MINOR.PATCH`, e.g. `1.0.0`.
  Currently, it creates a release on GitHub where the description is automatically generated from pull requests and issues that are closed in the release.
  The releases are available at |gh_release|.


Rulesets
--------

Under https://github.com/openSUSE/docbuild/settings/rules we have rulesets to protect the default branch and tags that matches the semantic versioning format.