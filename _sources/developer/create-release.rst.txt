.. _create-release:

Creating a New Release
======================

To create a new release, follow these steps:

#. Ensure that you have the latest changes from the main branch of the repository.
#. Create a new branch named ``release/<VERSION>``, where ``<VERSION>`` is the version number you are releasing (e.g., ``release/1.0.0``).
#. :ref:`Bump the version <bump-version>`.
#. :ref:`Update the project <update-project>`.
#. :ref:`Build the changelog <build-changelog>`.
#. Wait for the CI to pass. If it fails, fix the issues and commit again.
#. If the CI passes, (squash-)merge your release branch into the main branch.
   The GitHub Action workflow will automatically create a new release based on the name of the release branch.
#. Find the release in the GitHub repository under the |gh_release| section.