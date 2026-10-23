docbuild.models.manifest.Document
=================================

.. py:class:: docbuild.models.manifest.Document(/, **data: Any)

   Bases: :py:obj:`pydantic.BaseModel`

   .. autoapi-inheritance-diagram:: docbuild.models.manifest.Document
      :parts: 1


   Represents a single document within the manifest.

   .. code-block:: json

       {
           "docs": [
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
           ],
           "tasks": ["About"],
           "products": [{"name": "SUSE Linux", "versions": ["16.0"]}],
           "docTypes": [],
           "isGated": false,
           "rank": ""
       }


   .. py:method:: coerce_rank(value: str | int | None) -> int | None
      :classmethod:


      Coerce rank to an integer, treating empty strings or None as None to match legacy parity.



   .. py:method:: serialize_rank(value: int | str | None, info: pydantic.SerializationInfo) -> str

      Serialize rank to an empty string if None to match legacy parity.


