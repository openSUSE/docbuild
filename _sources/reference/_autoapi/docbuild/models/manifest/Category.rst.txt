docbuild.models.manifest.Category
=================================

.. py:class:: docbuild.models.manifest.Category(/, **data: Any)

   Bases: :py:obj:`pydantic.BaseModel`

   .. autoapi-inheritance-diagram:: docbuild.models.manifest.Category
      :parts: 1


   Represents a category for a product/docset.

   .. code-block:: json

       {
           "categoryId": "about",
           "rank": 1,
           "translations": [
               {
                   "lang": "en-us",
                   "default": true,
                   "title": "About"
               }
           ]
       }

