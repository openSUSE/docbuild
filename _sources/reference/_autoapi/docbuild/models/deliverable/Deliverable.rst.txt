docbuild.models.deliverable.Deliverable
=======================================

.. py:class:: docbuild.models.deliverable.Deliverable

   Deliverable model class operated on a validated config.

   * DeliverableXMLView owns facts you can derive from the XML node alone.
   * DeliverablePaths owns path construction.
   * Deliverable owns orchestration and non-XML domain objects.


   .. py:property:: xml
      :type: view.DeliverableXMLView


      Return the XML view of this deliverable.



   .. py:property:: paths
      :type: paths.DeliverablePaths


      Return the path helper for this deliverable.



   .. py:property:: pdlang
      :type: str


      Return product/docset/language identifier.



   .. py:property:: pdlangdc
      :type: str


      Return product/docset/language plus DC filename identifier.



   .. py:property:: full_id
      :type: str


      Return the canonical unique identifier for this deliverable.



   .. py:property:: docsuite
      :type: str


      Return docsuite identifier in ``product/docset/lang:dc`` format.



   .. py:property:: lang_is_default
      :type: bool


      Return ``True`` when the language node is marked as default.



   .. py:property:: branch
      :type: str


      Return the branch for this deliverable, with fallback lookup.



   .. py:property:: subdir
      :type: str


      Return configured subdirectory or an empty string.



   .. py:property:: git
      :type: docbuild.models.repo.Repo


      Return the Git repository configuration for this deliverable.



   .. py:property:: format
      :type: dict[Literal['html', 'single-html', 'pdf', 'epub'], bool]


      Return enabled output formats normalized to booleans.



   .. py:property:: metafile
      :type: str | None


      Return the metadata file path.



   .. py:property:: meta
      :type: docbuild.models.metadata.Metadata | None


      Return parsed metadata for this deliverable.



   .. py:method:: __hash__() -> int

      Return a hash based on the stable full identifier.



   .. py:method:: __repr__() -> str

      Return a concise debug representation of this deliverable.



   .. py:method:: make_safe_name(name: str) -> str
      :staticmethod:


      Normalize a string for safe use in filenames and path fragments.


