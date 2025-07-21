.. _create-release:

Creating a New Release
======================

When you are ready to release a new version of the project, start with creating a new release branch. There you bump the version, build the changelog, and adjust minor things like the documentation. Avoid commiting changes that introduces new features or add breaking changes.

Follow these steps:

#. Ensure that you have the latest changes from the main branch of the repository.
#. Create a new branch named ``release/<VERSION>``, where ``<VERSION>`` is the version number you are releasing (e.g., ``release/1.0.0``).
#. :ref:`Bump the version <bump-version>`.
#. :ref:`Update the project <update-project>`.
#. :ref:`Build the changelog <build-changelog>`.
#. In your current branch, push the branch to the remote repository:

   .. code-block:: console

      git push origin HEAD

#. Wait for the CI to pass. If it fails, fix the issues and commit again.
#. If the CI passes, (squash-)merge your release branch into the main branch.
   The GitHub Action workflow will automatically create a new release based on the name of the release branch.
#. Find the release in the GitHub repository under the |gh_release| section.
