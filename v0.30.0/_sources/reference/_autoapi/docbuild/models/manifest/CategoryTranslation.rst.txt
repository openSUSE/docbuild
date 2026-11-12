docbuild.models.manifest.CategoryTranslation
============================================

.. py:class:: docbuild.models.manifest.CategoryTranslation(/, **data: Any)

   Bases: :py:obj:`pydantic.BaseModel`

   .. autoapi-inheritance-diagram:: docbuild.models.manifest.CategoryTranslation
      :parts: 1


   Represents a translation for a category title.

   .. code-block:: json

       {
           "lang": "en-us",
           "default": true,
           "title": "About"
       }


   .. py:method:: set_default_for_english() -> Self

      Auto-mark English translations as default when not explicitly set.



   .. py:method:: serialize_lang(value: docbuild.models.language.LanguageCode, info: pydantic.SerializationInfo) -> str

      Serialize LanguageCode to a string like 'en-us'.


