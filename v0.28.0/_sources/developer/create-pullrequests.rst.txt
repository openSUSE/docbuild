.. _create-prs:

Create Pull Requests
====================

This section outlines the steps for creating pull requests (PRs) for this project.

It is assumed that you already cloned or forked this repostitory and have a working development environment set up.

Follow these steps to create a pull request:

#. On the GitHub project, find a bug or feature you want to work on.
#. In your local repository, create a new branch for your changes.

   It's recommended to use the issue number and a descriptive name for the branch that reflects the changes you plan to make.
#. Make your changes in the codebase.

   * Ensure that you :ref:`run the test suite <run-testsuite>`.
   * Watch for the :ref:`coverage report <interprete-coverage>` and try to keep the coverage high.
   * Enhance the documentation if it's a user-facing change.
#. Commit your changes with a clear and concise commit message.

   * Include the issue number if applicable and add phrases like ``Fixes #123``.
   * It's enough to have a high-level description of the changes.
   * The message should explain *why* these changes were necessary.
#. Push your changes and create a pull request On GitHub. GitHub creates a pull request number for you.
#. If useful, :ref:`create a news fragment <add-newsfragments>` of your changes.

   This is important for the changelog generation. Push the news fragment to the same branch as your changes.
#. On GitHub, request a review.
#. Address any feedback from the review.

   * Make additional commits to your branch as needed.
   * Ensure that the test suite passes after your changes.
#. Once the review is complete and all tests pass, squash merge your branch into the main branch.
