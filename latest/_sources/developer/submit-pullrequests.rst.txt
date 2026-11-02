.. _submit-prs:

Submitting a Pull Request
=========================

This section outlines the steps for creating pull requests (PRs) for this project. Before you start, ensure you :ref:`forked the project <fork-project>`.



Making and submitting your changes
----------------------------------

Prepare your changes for review:

#. Ensure your fork is up to date with the upstream repository. This is crucial to avoid conflicts and ensure you are working with the latest changes.

#. Create a branch in your fork. It's recommended to use the issue number and a descriptive name for the branch that reflects the changes you plan to make.

#. Make your changes in the codebase.

   * Ensure that you :ref:`run the test suite <run-testsuite>`.
   * Watch for the :ref:`coverage report <interprete-coverage>` and try to keep the coverage high.
   * Enhance the documentation if it's a user-facing change.

#. :ref:`Create a news fragment <add-newsfragments>` file about your changes and add it to the same branch.

#. Commit your changes with a clear and concise commit message.

   * Include the issue number if applicable and add phrases like ``Fixes #123``.
   * It's enough to have a high-level description of the changes.
   * The message should explain *why* these changes were necessary.

#. `Push your branch to your fork <https://docs.github.com/en/get-started/using-git/pushing-commits-to-a-remote-repository>`_.

#. `Open a pull request from your fork <https://docs.github.com/en/pull-requests/how-tos/create-pull-requests/creating-a-pull-request-from-a-fork>`_ on GitHub with a description of your changes and their purpose.

#. `Request a review <https://docs.github.com/en/pull-requests/how-tos/create-pull-requests/requesting-a-pull-request-review>`_ on GitHub.


Reviewing and merging
---------------------

Complete the review process:

#. Address any feedback from the review. Make additional commits to your branch as needed.

#. If ``main`` has advanced, update your branch and resolve any conflicts.

#. Ensure that the test suite passes after addressing feedback.

#. Wait for the maintainers to merge your pull request after the review is complete and all tests pass.
