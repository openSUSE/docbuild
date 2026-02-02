docbuild.models.manifest.Document
=================================

.. py:class:: docbuild.models.manifest.Document(/, **data: Any)

   Bases: :py:obj:`pydantic.BaseModel`

   .. autoapi-inheritance-diagram:: docbuild.models.manifest.Document
      :parts: 1


   Represents a single document within the manifest.


   .. py:method:: coerce_rank(value: str | int | None) -> int | None
      :classmethod:


      Coerce rank from string to int, handling empty strings.



   .. py:method:: serialize_rank(value: int | str | None, info: pydantic.SerializationInfo) -> str

      Serialize rank to an empty string if None.


