docbuild.models.deliverable.paths.DeliverablePaths
==================================================

.. py:class:: docbuild.models.deliverable.paths.DeliverablePaths

   Path-related properties for a deliverable.


   .. py:property:: product_docset
      :type: str


      Return product and docset joined by a slash.



   .. py:property:: relpath
      :type: str


      Return the relative path of the deliverable.



   .. py:property:: zip_path
      :type: str


      Return the path to the ZIP file.



   .. py:method:: base_format_path(fmt: str) -> str

      Return the base path for a given format.



   .. py:property:: html_path
      :type: str


      Return the path to the HTML directory.



   .. py:property:: singlehtml_path
      :type: str


      Return the path to the single-HTML directory.



   .. py:property:: pdf_path
      :type: str


      Return the path to the PDF file.



   .. py:method:: __repr__() -> str

      Return a string representation of the deliverable paths.


