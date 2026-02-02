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


   .. py:method:: serialize_lang(value: docbuild.models.language.LanguageCode, info: pydantic.SerializationInfo) -> str

      Serialize LanguageCode to a string like 'en-us'.



   .. py:method:: from_xml_node(node: lxml.etree._Element) -> collections.abc.Generator[Self, None, None]
      :classmethod:


      Extract descriptions from a parent XML node.

      :param node: a node pointing to ``<product>``
      :yield:


