docbuild.models.manifest.Archive
================================

.. py:class:: docbuild.models.manifest.Archive(/, **data: Any)

   Bases: :py:obj:`pydantic.BaseModel`

   .. autoapi-inheritance-diagram:: docbuild.models.manifest.Archive
      :parts: 1


   Represents an archive (e.g., a ZIP file) for a product/docset.

   .. code-block:: json

       {
           "lang": "en-us",
           "default": true,
           "zip": "/en-us/sles/16.0/sles-16.0-en-us.zip"
       }


   .. py:method:: serialize_lang(value: docbuild.models.language.LanguageCode, info: pydantic.SerializationInfo) -> str

      Serialize LanguageCode to a string like 'en-us'.


