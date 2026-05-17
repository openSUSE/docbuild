docbuild.models.repo.Repo
=========================

.. py:class:: docbuild.models.repo.Repo(value: str, default_branch: str | None = None)

   A repository model that can be initialized from a URL or a short name.

   This model can be compared directly with strings, which will check
   against the repository's abbreviated name (e.g., ``org/repo``).

   Two Repo objects are considered equal if their derived names are the same,
   regardless of the original URL (HTTPS vs. SSH).

   The class understands:

   *  A full URL like ``https://HOST/ORG/REPO.git`` or a URL pointing
      to a branch like ``https://HOST/ORG/REPO/tree/BRANCH``

   *  A SSH URL like ``git@HOST:ORG/REPO.git``.

   *  An abbreviated URL like ``SERVICE://ORG/REPO`` or ``SERVICE://ORG/REPO.git``
      The service part is a two to four letter alias for common Git hosting
      services, for example:

      * ``gh`` for GitHub (default)
      * ``gl`` for GitLab
      * ``bb`` for BitBucket
      * ``gt`` for Gitea
      * ``cb`` for Codeberg
      * ``ghe`` for GitHub Enterprise

      This makes the reference to a Git repo more readable.

   *  A plain notation like ``ORG/REPO`` which defaults to GitHub.

   Additionally, branches other than default branches (main or master) can be
   added by ``@BRANCH_NAME`` to any of the above URLs.

   .. code-block:: python

       >>> from docbuild.models.repo import Repo
       >>> repo = Repo("https://github.com/openSUSE/docbuild.git")
       >>> repo.url
       'https://github.com/openSUSE/docbuild.git'
       >>> repo.name
       'openSUSE/docbuild'
       >>> repo.surl
       'gh://openSUSE/docbuild'
       >>> repo.treeurl
       'https://github.com/openSUSE/docbuild/tree/main'



   .. py:attribute:: DEFAULT_HOST
      :type:  ClassVar[str]
      :value: 'https://github.com'


      The default host to use when constructing a URL from a short name.



   .. py:attribute:: url
      :type:  str

      The full URL of the repository.



   .. py:attribute:: treeurl
      :type:  str

      The full URL including the branch of the repository.



   .. py:attribute:: surl
      :type:  str

      The shortened URL version of the repository, for example gh://org/repo for
      a GitHub repo.



   .. py:attribute:: name
      :type:  str

      The abbreviated name of the repository (e.g., 'org/repo').



   .. py:attribute:: branch
      :type:  str | None

      The branch of the repository



   .. py:attribute:: origin
      :type:  str

      The original unchanged URL of the repository.



   .. py:method:: __eq__(other: object) -> bool

      Compare Repo with another Repo (by name) or a string (by name).



   .. py:method:: __str__() -> str

      Return the canonical URL of the repository.



   .. py:method:: __hash__() -> int

      Hash the Repo object based on its canonical derived name.



   .. py:method:: __contains__(item: str) -> bool

      Check if a string is part of the repository's abbreviated name.



   .. py:property:: slug
      :type: str


      Return the slug name of the repository.


