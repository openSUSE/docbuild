.. _clone-repositories:

Cloning Repositories
====================

During the process of building documentation, the script clones Git repositores into the permanent storage directory as needed. In case you need to clone repositories manually, you can use the following commands:

.. code-block:: shell
   :caption: Synopsis of :command:`docbuild repo clone`

   $ docbuild repo clone [OPTIONS] REPO [REPO ...]

The ``REPO`` argument can be specified in various formats, such as:

* A full URL like ``https://github.com/org/repo.git``.
* An SSH URL like ``git@github.com:org/repo.git``.
* An abbreviated URL like ``SERVICE://org/repo``. Currently the following service prefixes are supported:

  * ``gh://`` for GitHub
  * ``gl://`` for GitLab
  * ``gls://`` for GitLab SUSE (gitlab.suse.de)
  * ``bb://`` for Bitbucket
  * ``ghe://`` for GitHub Enterprise
  * ``gt://`` for Gitea
  * ``cb://`` for Codeberg

* An abbreviated name like ``org/repo`` which defaults to GitHub.

All notations are treated the same and normalized. That includes transforming the URL to lowercase and removing trailing slashes.

For example, to clone the ``https://github.com/SUSE/doc-modular.git`` repository, the following notations are equivalent:

.. code-block:: shell
   :caption: Example of cloning a repository
   :name: docbuild-repo-clone

   $ docbuild repo clone https://github.com/SUSE/doc-modular.git
   $ docbuild repo clone gh://SUSE/doc-modular
   $ docbuild repo clone gh://suse/doc-modular
   $ docbuild repo clone SUSE/doc-modular

The command will clone the repository into the permanent storage directory.
You can find the exact path by running:

.. code-block:: shell
   :caption: Find the permanent storage directory
   :name: docbuild-repo-dir

   $ docbuild repo dir
   /var/cache/docbuild/repos/permanent-full/

To get a list of all available repositories in the permanent storage, use:

.. code-block:: shell
   :caption: List all repositories in permanent storage
   :name: docbuild-repo-list

   $ docbuild repo list