.. _create-release:

Creating a New Release
======================

A release is a snapshot of the project at a specific point in time, typically
associated with a version number. It represents a stable and tested state of
the project that can be shared with users. Creating a release involves several
steps to ensure that the project is properly packaged, documented, and ready
for distribution.

Ensure the the following pre-requisites are met before starting the release process:

* You have pulled the latest changes from the main branch of the repository.
* You have the necessary permissions to create a release.

Follow these steps:

#. Create a new branch named ``release/<VERSION>``, where ``<VERSION>`` is the version number you are releasing (e.g., ``release/1.0.0``).
#. :ref:`Bump the version <bump-version>`.
#. :ref:`Update the project <update-project>`.
#. :ref:`Build the changelog <build-changelog>`.
#. :ref:`Build the documentation <build-docs>`.
#. Optionally, look for Ruff issues:

   .. code-block:: console

      ruff check .

#. In your current branch, push the branch to the remote repository:

   .. code-block:: console

      git push -u origin HEAD

#. Wait for the CI to pass.

   * If it fails, fix the issues and commit again.
   * If the CI passes, (squash-)merge your release branch into the main branch.
     The GitHub Action workflow will automatically create a new release based on the name of the release branch.

Find the new release in the GitHub repository under the |gh_release| section.
