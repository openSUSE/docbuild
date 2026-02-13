docbuild.models.manifest.SingleDocument
=======================================

.. py:class:: docbuild.models.manifest.SingleDocument(/, **data: Any)

   Bases: :py:obj:`pydantic.BaseModel`

   .. autoapi-inheritance-diagram:: docbuild.models.manifest.SingleDocument
      :parts: 1


   Represent a single document.

   .. code-block:: json

       {
           "lang": "en",
           "default": true,
           "title": "Key Differences Between SLE 15 and SLE 16",
           "subtitle": "Adopting SLE 16",
           "description": "Key differences between SLE 15 and SLE 16",
           "dcfile": "DC-SLE-comparison",
           "rootid": "comparison-sle16-sle15",
           "format": {
               "html": "/sles/16.0/html/SLE-comparison/",
               "pdf": "/sles/16.0/pdf/SLE-comparison_en.pdf"
           },
           "dateModified": "2026-04-01"
       }


   .. py:method:: serialize_date(value: datetime.date | None, info: pydantic.SerializationInfo) -> str

      Serialize date to 'YYYY-MM-DD' or an empty string if None.


