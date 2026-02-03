docbuild.models.manifest.SingleDocument
=======================================

.. py:class:: docbuild.models.manifest.SingleDocument(/, **data: Any)

   Bases: :py:obj:`pydantic.BaseModel`

   .. autoapi-inheritance-diagram:: docbuild.models.manifest.SingleDocument
      :parts: 1


   Represent a single document.


   .. py:method:: serialize_date(value: datetime.date | None, info: pydantic.SerializationInfo) -> str

      Serialize date to 'YYYY-MM-DD' or an empty string if None.


