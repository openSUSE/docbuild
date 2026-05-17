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


   .. py:method:: reset_rank() -> None
      :classmethod:


      Reset the rank counter.



   .. py:method:: from_xml_node(node: lxml.etree._Element) -> collections.abc.Generator[Self, None, None]
      :classmethod:


      Extract categories from a parent XML node.

      :param node: a node pointing to ``<product>``
      :yield: A :class:`Category` instance for each category found.


