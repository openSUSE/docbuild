docbuild.models.deliverable.Deliverable
=======================================

.. py:class:: docbuild.models.deliverable.Deliverable

   A class to represent a deliverable.

   Usually called with a ``<deliverable>`` node from the XML
   configuration file. It contains information about the product,
   docset, language, branch, and other metadata related to the
   deliverable.


   .. py:property:: productid
      :type: str


      Return the product ID.



   .. py:property:: docsetid
      :type: str


      Return the docset ID.



   .. py:property:: lang
      :type: str


      Returns the language and country code (e.g., 'en-us').



   .. py:property:: language
      :type: str


      Returns only the language (e.g., 'en').



   .. py:property:: product_docset
      :type: str


      Returns product and docset.



   .. py:property:: pdlang
      :type: str


      Return product, docset, and language.



   .. py:property:: pdlangdc
      :type: str


      Return product, docset, language and DC filename.



   .. py:property:: full_id
      :type: str


      Return the full ID of the deliverable.



   .. py:property:: lang_is_default
      :type: bool


      Check if the language is the default language.



   .. py:property:: docsuite
      :type: str


      Return the product, docset, language and the DC filename.



   .. py:property:: branch
      :type: str


      Return the branch where to find the deliverable.

      Searches for the branch in the English language node first,
      then in the current language node.

      :return: The branch name as a string.
      :raises ValueError: If no branch is found



   .. py:property:: subdir
      :type: str


      Return subdirectory or an empty string if not found.



   .. py:property:: git
      :type: docbuild.models.repo.Repo


      Return the git repository.

      :return: The git remote URL as a string.
      :raises ValueError: If no git remote is found for the deliverable.



   .. py:property:: dcfile
      :type: str


      Return the DC filename or None if not found.



   .. py:property:: basefile
      :type: str


      Return the DC filename without the DC prefix.



   .. py:property:: format
      :type: dict[Literal['html', 'single-html', 'pdf', 'epub'], bool]


      Return the formats of the deliverable.

      Normalize the format attributes to boolean values.

      :return: A dictionary with format names as keys and boolean values.
      :raises ValueError: If no format is found for the deliverable.



   .. py:property:: node
      :type: lxml.etree._Element


      Return the node of the deliverable.



   .. py:property:: productname
      :type: str


      Return the product name or None if not found.



   .. py:property:: acronym
      :type: str


      Return the product acronym or None if not found.



   .. py:property:: version
      :type: str


      Return the version of the docset or None if not found.



   .. py:property:: lifecycle
      :type: str


      Return the lifecycle of the docset.



   .. py:property:: relpath
      :type: str


      Return the relative path of the deliverable.



   .. py:property:: repo_path
      :type: pathlib.Path


      Return the "slug" path of the repository.



   .. py:property:: zip_path
      :type: str


      Return the path to the ZIP file.



   .. py:property:: html_path
      :type: str


      Return the path to the HTML directory.



   .. py:property:: singlehtml_path
      :type: str


      Return the path to the single HTML directory.



   .. py:property:: pdf_path
      :type: str


      Return the path to the PDF file.



   .. py:property:: product_node
      :type: lxml.etree._Element


      Return the product node of the deliverable.



   .. py:property:: docset_node
      :type: lxml.etree._Element


      Return the docset node of the deliverable.



   .. py:property:: metafile
      :type: str | None


      Return the metadata file.



   .. py:property:: meta
      :type: docbuild.models.metadata.Metadata | None


      Return the metadata object of the deliverable.



   .. py:method:: __hash__() -> int

      Implement hash(self).



   .. py:method:: __repr__() -> str

      Implement repr(self).



   .. py:method:: to_dict() -> dict
      :abstractmethod:


      Return the deliverable as a JSON object.



   .. py:method:: make_safe_name(name: str) -> str
      :staticmethod:


      Make a name safe for use in a filename or directory.


