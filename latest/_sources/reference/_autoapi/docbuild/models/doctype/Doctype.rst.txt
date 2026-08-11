docbuild.models.doctype.Doctype
===============================

.. py:class:: docbuild.models.doctype.Doctype(/, **data: Any)

   Bases: :py:obj:`pydantic.BaseModel`

   .. autoapi-inheritance-diagram:: docbuild.models.doctype.Doctype
      :parts: 1


   A "doctype" that comprises of a product, docset, lifecycle, and language.

   The format has the following syntax:

   .. code-block:: text

      [/]?PRODUCT/DOCSETS[@LIFECYCLES]/[LANGS]

   The placeholders mean the following:

   * ``PRODUCT``: a lowercase acronym of a SUSE product, e.g. ``sles``
   * ``DOCSETS``: one or more docsets of the mentioned product, separated by comma
   * ``LIFECYCLES``: zero or more lifecycles, separated by comma or pipe.
     Default to ``unknown`` if omitted.
   * ``LANGS``: zero or more languages, separated by comma.
     Default to English (``en-us``) if omitted.

   :raises pydantic_core.ValidationError: if the input values are invalid.

   >>> doctype = Doctype.from_str("sles/15-SP6@supported/en-us,de-de")
   >>> doctype.product
   <Product.sles: 'sles'>
   <Product.sles: 'SUSE Linux Enterprise Server'>
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



   .. py:method:: iter_doctypes(portal_root: lxml.etree._Element | None = None) -> collections.abc.Iterator[Doctype]

      Iterate over all docset and language combinations.

      The iteration order is docset-major: for each docset, iterate all
      languages. This is the Cartesian product of ``docset`` and ``langs``.

      If ``portal_root`` is given, wildcard values (``*``) are expanded from
      the parsed portal XML tree. Without ``portal_root``, wildcards remain
      symbolic.

      >>> doctype = Doctype.from_str("sles/15-SP6,15-SP7/en-us,de-de")
      >>> [
      ...     f"{item.product.value}/{item.docset[0]}/{item.langs[0].language}"
      ...     for item in doctype.iter_doctypes()
      ... ]
      ['sles/15-SP6/de-de', 'sles/15-SP6/en-us', 'sles/15-SP7/de-de', 'sles/15-SP7/en-us']



   .. py:method:: coerce_product(value: str | docbuild.models.product.Product) -> docbuild.models.product.Product
      :classmethod:


      Convert a string into a valid Product.



   .. py:method:: coerce_docset(value: str | list[str]) -> list[str]
      :classmethod:


      Convert a string into a list.



   .. py:method:: coerce_langs(value: str | list[str | docbuild.models.language.LanguageCode]) -> list[docbuild.models.language.LanguageCode]
      :classmethod:


      Convert a comma-separated string or a list of strings into LanguageCode.



   .. py:method:: from_str(doctype_str: str, *, default_lang: str = 'en-us') -> Doctype
      :classmethod:


      Parse a string that adheres to the doctype format.

      :param doctype_str: A string that adheres to the doctype format.
      :param default_lang: The default language to use if none is specified (by default, "en-us").
      :return: A Doctype object.
      :raise ValueError: If the input string is invalid.

      The language segment is optional: ``sles/16`` and ``sles/16/`` all select
      English (``en-us``) by default, while ``sles/16/*`` and ``sles/16@supported/*``
      are all equivalent and select *all* languages.



   .. py:method:: xpath(absolute: bool = False) -> str

      Return an XPath expression for this Doctype to find all deliverables.

      >>> result = Doctype.from_str("sles/15-SP6@supported/en-us,de-de").xpath(absolute=True)
      >>> expected = (
      ...     "//product[@id='sles']/docset[@path='15-SP6']"
      ...     "[@lifecycle='supported']"
      ...     "/resources/locale[@lang='de-de' or @lang='en-us']"
      ...     "/deliverable"
      ... )
      >>> result == expected
      True

      :return: An XPath expression that can be used to find all
          deliverables that match this Doctype.



   .. py:method:: product_xpath_segment() -> str

      Return the XPath segment for the product node.

      Example: "product[@id='sles']" or "product"



   .. py:method:: docset_xpath_segment(docset: str | None = None) -> str

      Return the XPath segment for the docset node.

      Example: "docset[@path='15-SP6']" or "docset"



   .. py:method:: lifecycle_xpath_segment() -> str

      Return the XPath segment for the lifecycle node.

      Example: "docset[@lifecycle='supported']" or "docset"



   .. py:method:: locale_xpath_segment() -> str

      Return the XPath segment for the language node.

      Example: "resources/locale[@lang='en-us']" or "resources/locale"


