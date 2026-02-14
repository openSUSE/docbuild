docbuild.models.manifest.Description
====================================

.. py:class:: docbuild.models.manifest.Description(/, **data: Any)

   Bases: :py:obj:`pydantic.BaseModel`

   .. autoapi-inheritance-diagram:: docbuild.models.manifest.Description
      :parts: 1


   Represents a description for a product/docset.

   .. code-block:: json

       {
           "lang": "en-us",
           "default": true,
           "description": "<p>The English description for a product.</p>"
       }

