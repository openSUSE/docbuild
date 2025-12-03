docbuild.models.language.LanguageCode
=====================================

.. py:class:: docbuild.models.language.LanguageCode(/, **data: Any)

   Bases: :py:obj:`pydantic.BaseModel`

   .. autoapi-inheritance-diagram:: docbuild.models.language.LanguageCode
      :parts: 1


   The language in the format language-country (all lowercase).

   It accepts also an underscore as a separator instead of a dash.
   Use "*" to denote "ALL" languages


   .. py:attribute:: language
      :type:  str
      :value: None


      The natural language in the format ll-cc, where 'll' is the
      language and 'cc' the country.



   .. py:attribute:: model_config

      Configuration for the model, should be a dictionary
      conforming to Pydantic's :class:`~pydantic.config.ConfigDict`.



   .. py:attribute:: ALLOWED_LANGS
      :type:  ClassVar[frozenset]

      Class variable containing all allowed languages.



   .. py:method:: __str__() -> str

      Implement str(self).



   .. py:method:: __repr__() -> str

      Implement repr(self).



   .. py:method:: __eq__(other: object|str|LanguageCode) -> bool

      Implement self == other.

      The comparison does NOT break the principle of equality:
      * Reflexive: a == b
      * Symmetric: a == b <=> b == a
      * Transitive: if a == b and b == c, then a == c

      If you need to check for wildcar logic, use matches()



   .. py:method:: __lt__(other: object|str|LanguageCode) -> bool

      Implement self < other.

      Special properties:
      - "*" is always the "smallest" language
      - If self contains "*" and the other not, return True
      - If self and the other contains "*", return False



   .. py:method:: __hash__() -> int

      Implement hash(self).

      For using 'in sets' or as dict keys



   .. py:method:: matches(other: LanguageCode | str) -> bool

      Return True if this LanguageCode matches the other, considering wildcards.

      The string '*' matches any language:

      >>> LanguageCode("*").matches("de-de")
      True
      >>> LanguageCode("de-de").matches("*")
      True



   .. py:method:: validate_language(value: str) -> str
      :classmethod:


      Check if the passed language adheres to the allowed language.



   .. py:method:: lang() -> str

      Extract the language part of the language code (property).



   .. py:method:: country() -> str

      Extract the country part of the language code (property).


