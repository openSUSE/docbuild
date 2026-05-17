docbuild.models.deliverable.view.DeliverableXMLView
===================================================

.. py:class:: docbuild.models.deliverable.view.DeliverableXMLView

   Common Portal/XML facade for a deliverable node.


   .. py:property:: product_node
      :type: lxml.etree._Element


      Return the ancestor ``<product>`` element.



   .. py:property:: docset_node
      :type: lxml.etree._Element


      Return the ancestor ``<docset>`` element.



   .. py:property:: productid
      :type: str


      Return the product ID (``<product id=…>``) or None if absent..



   .. py:property:: product_docset
      :type: str


      Return the product/docset ID (``<product id=…>/<docset id=…>``).



   .. py:property:: productname
      :type: str | None


      Return the product name from ``<product><name>`` or None if absent.



   .. py:property:: acronym
      :type: str


      Return the product acronym, or an empty string if absent.



   .. py:property:: docsetrealid
      :type: str | None


      Return the docset real ID (``<docset id=…>``) or None if absent.



   .. py:property:: docsetid
      :type: str | None


      Return the docset path/name (``<docset path=…>``), NOT the real ID.



   .. py:property:: lang
      :type: docbuild.models.language.LanguageCode


      Return the language and country code (e.g. ``'en-us'``).



   .. py:property:: dcfile
      :type: str | None


      Return the DC filename, or ``None`` if absent.



   .. py:property:: basefile
      :type: str | None


      Return :attr:`dcfile` stripped of its ``DC-`` prefix.



   .. py:property:: kind
      :type: str | None


      Return the deliverable type from ``@type`` or ``None`` if absent.



   .. py:property:: is_prebuilt
      :type: bool


      Return True if the deliverable is marked as prebuilt.



   .. py:property:: is_dc
      :type: bool


      Return True if the deliverable is marked as DC.



   .. py:property:: is_ref
      :type: bool


      Return True if the deliverable is marked as a reference.



   .. py:method:: categories() -> collections.abc.Generator[lxml.etree._Element, None, None]

      Yield all ``<category>`` elements under the product node.



   .. py:method:: categories_from_root() -> collections.abc.Generator[lxml.etree._Element, None, None]

      Yield all ``<category>`` elements under the root node .



   .. py:property:: all_categories
      :type: collections.abc.Generator[lxml.etree._Element, None, None]


      Return product and root-level category elements.



   .. py:method:: desc() -> collections.abc.Generator[lxml.etree._Element, None, None]

      Yield product ``<desc>`` elements.



   .. py:method:: branch() -> str | None

      Return branch from current language or ``None`` if missing.



   .. py:method:: branch_from_fallback_locale() -> str | None

      Return branch from fallback locale lookup or ``None`` if missing.



   .. py:method:: subdir() -> str

      Return subdirectory or empty string.



   .. py:method:: git_remote() -> docbuild.models.repo.Repo | None

      Return git remote URL from sibling ``<git>`` node.



   .. py:method:: format_attrs() -> dict[Literal['epub', 'html', 'pdf', 'single-html'], bool] | None

      Return deliverable output formats as a boolean dict.

      Extracts format attributes from the XML element, converts their
      values to booleans, and returns a complete dict with all expected
      formats (defaulting missing keys to False). Returns None if no
      format element is found.



   .. py:method:: __str__() -> str

      Return a human-readable string representation of the deliverable.



   .. py:method:: __repr__() -> str

      Return a concise string representation of the deliverable.


