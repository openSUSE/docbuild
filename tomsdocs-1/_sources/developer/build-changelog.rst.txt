.. _build-changelog:

Building the Changelog
======================

The changelog is built from news fragments that are added to the repository. These fragments are collected and assembled into a changelog file for each new release.

To build the changelog, make sure you have:

* added news fragments (see :ref:`add-newsfragments`)
* updated the project (see :ref:`update-project`)

#. If needed, :ref:`bump the version <bump-version>`.
#. Build the changelog file from all news fragments:

   .. code-block:: shell-session
      :caption: Build a combined changelog from news fragments

      towncrier build [--yes]

   After this command, the :file:`CHANGELOG.rst` file in the root directory is updated and all news fragments are removed from the directory :file:`changelog.d/`.

#. Review the :file:`CHANGELOG.rst` file. Sometimes the changelog may not look as expected, especially if the news fragments are not formatted correctly. You can edit the file manually to fix any issues.

#. Commit the :file:`CHANGELOG.rst` and the :file:`changelog.d/` directory with a message that describes the change.