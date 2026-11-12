docbuild.models.metadata.Metadata
=================================

.. py:class:: docbuild.models.metadata.Metadata

   A class to represent the metadata of a deliverable.


   .. py:attribute:: title
      :type:  str | None
      :value: None


      The title of the deliverable.



   .. py:attribute:: subtitle
      :type:  str
      :value: ''


      The subtitle of the deliverable.



   .. py:attribute:: seo_title
      :type:  str | None
      :value: None


      The SEO title of the deliverable.



   .. py:attribute:: seo_description
      :type:  str
      :value: ''


      The SEO description of the deliverable.



   .. py:attribute:: seo_social_descr
      :type:  str
      :value: ''


      The SEO social description of the deliverable.



   .. py:attribute:: dateModified
      :type:  str
      :value: ''


      The date when the deliverable was last modified.



   .. py:attribute:: tasks
      :type:  list[str]
      :value: []


      A list of tasks related to the deliverable.



   .. py:attribute:: series
      :type:  str | None
      :value: None


      The series of the deliverable, if applicable.



   .. py:attribute:: rootid
      :type:  str | None
      :value: None


      The root ID of the deliverable, if applicable.



   .. py:attribute:: products
      :type:  list[dict]
      :value: []


      A list of products related to the deliverable, each represented
      as a dictionary.



   .. py:method:: read(metafile: pathlib.Path | str) -> Self

      Read the metadata from a file.

      :param metafile: The path to the metadata file.
      :return: The metadata instance.


