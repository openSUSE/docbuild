docbuild.models.repo.Repo
=========================

.. py:class:: docbuild.models.repo.Repo(value: str)

   A repository model that can be initialized from a URL or a short name.

   This model can be compared directly with strings, which will check
   against the repository's abbreviated name (e.g., 'org/repo').

   Two Repo objects are considered equal if their derived names are the same,
   regardless of the original URL (HTTPS vs. SSH).


   .. py:attribute:: DEFAULT_HOST
      :type:  ClassVar[str]
      :value: 'https://github.com'


      The default host to use when constructing a URL from a short name.



   .. py:attribute:: url
      :type:  str

      The full URL of the repository.



   .. py:attribute:: surl
      :type:  str

      The shortened URL version of the repository, for example gh://org/repo for
      a GitHub repo.



   .. py:attribute:: name
      :type:  str

      The abbreviated name of the repository (e.g., 'org/repo').



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


