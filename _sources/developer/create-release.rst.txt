.. _create-release:

Creating a New Release
======================

To create a new release, follow these steps:

#. Ensure that you have the latest changes from the main branch of the repository.
#. Create a new branch for your release. The branch name should follow the format: ``release/<VERSION>``, where ``<VERSION>`` is the version number you are releasing (e.g., ``release/1.0.0``).
#. :ref:`Bump the version <bump-version>`.
#. :ref:`Update the project <update-project>`.
#. Build the changelog file from all news fragments:

   .. code-block:: shell-session
      :caption: Build a combined changelog from news fragment

      $ towncrier build [--yes]


#. Commit your changes with a message that describes the release.
#. Wait for the CI to pass. If it fails, fix the issues and commit again.
#. If the CI passes, (squash-)merge your release branch into the main branch.
#. Tag the commit in the ``main`` branch with the version number. The release process is triggered by this tag in the format ``MAJOR.MINOR.PATCH``.

   For example, if you are releasing version 1.1.0, you would tag the commit as follows:

   .. code-block:: shell-session
      :caption: Tag the release commit

       $ git tag 1.1.0
       $ git push origin 1.1.0

#. Find the release in the GitHub repository under the |gh_release| section.