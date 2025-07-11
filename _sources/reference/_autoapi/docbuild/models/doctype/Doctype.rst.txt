docbuild.models.doctype.Doctype
===============================

.. py:class:: docbuild.models.doctype.Doctype(/, **data: Any)

   Bases: :py:obj:`pydantic.BaseModel`

   .. autoapi-inheritance-diagram:: docbuild.models.doctype.Doctype
      :parts: 1


   A "doctype" that comprises of a product, docset, lifecycle, and language.

   >>> doctype = Doctype.from_str("sles/15-SP6@supported/en-us,de-de")
   >>> doctype.product
   <Product.sles: 'sles'>
   >>> doctype.docset
   ['15-SP6']
   >>> doctype.lifecycle.name
   'supported'
   >>> doctype.langs
   [LanguageCode(language='de-de'), LanguageCode(language='en-us')]


   .. py:attribute:: product
      :type:  docbuild.models.product.Product
      :value: None


      A SUSE product is a lowercase acronym



   .. py:attribute:: docset
      :type:  list[str]
      :value: None


      A specific 'docset' of a product (usually a release or version)



   .. py:attribute:: lifecycle
      :type:  docbuild.models.lifecycle.LifecycleFlag
      :value: None


      The state  (supported, beta, etc.) of the Doctype



   .. py:attribute:: langs
      :type:  list[docbuild.models.language.LanguageCode]
      :value: None


      A natural language containing language and country



   .. py:method:: __eq__(other: object) -> bool

      Check equality with another Doctype, ignoring order in docset/langs.



   .. py:method:: __lt__(other: object) -> bool

      Check if this Doctype is less than another Doctype.



   .. py:method:: __str__() -> str

      Implement str(self).



   .. py:method:: __repr__() -> str

      Implement repr(self).



   .. py:method:: __contains__(other: Doctype) -> bool

      Return if bool(other in self).

      Every part of a Doctype is compared element-wise.



   .. py:method:: __hash__() -> int

      Implement hash(self).



   .. py:method:: coerce_product(value: str | docbuild.models.product.Product) -> docbuild.models.product.Product
      :classmethod:


      Convert a string into a valid Product.



   .. py:method:: coerce_docset(value: str | list[str]) -> list[str]
      :classmethod:


      Convert a string into a list.



   .. py:method:: coerce_lifecycle(value: str | docbuild.models.lifecycle.LifecycleFlag) -> docbuild.models.lifecycle.BaseLifecycleFlag
      :classmethod:


      Convert a string into a LifecycleFlag.



   .. py:method:: coerce_langs(value: str | list[str | docbuild.models.language.LanguageCode]) -> list[docbuild.models.language.LanguageCode]
      :classmethod:


      Convert a comma-separated string or a list of strings into LanguageCode.



   .. py:method:: from_str(doctype_str: str) -> Self
      :classmethod:


      Parse a string that adheres to the doctype format.

      The format has the following syntax::

          [PRODUCT]/[DOCSETS][@LIFECYCLES]/LANGS

      Plural means you can have one or more items:

      * ``PRODUCT``: a lowercase acronym of a SUSE product, e.g. ``sles``
      * ``DOCSETS``: separated by comma
      * ``LIFECYCLES``: separated by comma or pipe
      * ``LANGS``: separated by comma



   .. py:method:: xpath() -> str

      Return an XPath expression for this Doctype to find all deliverables.

      >>> result = Doctype.from_str("sles/15-SP6@supported/en-us,de-de").xpath()
      >>> expected = (
      ...     "product[@productid='sles']/docset[@setid='15-SP6']"
      ...     "[@lifecycle='supported']"
      ...     "/builddocs/language[@lang='de-de' or @lang='en-us']"
      ... )
      >>> result == expected
      True

      :return: A relative XPath expression that can be used to find all
          deliverables that match this Doctype.


