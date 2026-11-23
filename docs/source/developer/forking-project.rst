
.. _fork-project:

Forking the Project
===================

Prepare a branch for your contribution:

.. steps::

   .. step:: Find an issue to work on

      On the GitHub project, find a bug or feature you want to work on and ask to be assigned to it.

   .. step:: Create a fork

      `Create a fork <https://docs.github.com/en/pull-requests/how-tos/work-with-forks/fork-a-repo>`_ of the repository under your GitHub account.

   .. step:: Clone your fork

      `Clone your fork <https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository>`_ to your local machine.

   .. step:: Create a branch for your changes

      In your local repository, create a new branch for your changes.

      It's recommended to use the issue number and a descriptive name for the branch that reflects the changes you plan to make.

   .. step:: Configure an upstream remote

      `Configure a remote upstream <https://docs.github.com/en/pull-requests/how-tos/work-with-forks/configuring-a-remote-repository-for-a-fork>`_ repository to keep your fork in sync with the original repository:

      .. code-block:: console

         $ git remote add upstream https://github.com/opensuse/docbuild.git
