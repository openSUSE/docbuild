docbuild.config.xml.stitch
==========================

.. py:module:: docbuild.config.xml.stitch

.. autoapi-nested-parse::

   Stitch file handling.



Functions
---------

.. autoapisummary::

   docbuild.config.xml.stitch.load_check_functions
   docbuild.config.xml.stitch.create_stitchfile


Module Contents
---------------

.. py:function:: load_check_functions() -> list[collections.abc.Callable]

   Load all check functions from :mod:`docbuild.config.xml.checks`.


.. py:function:: create_stitchfile(xmlfiles: collections.abc.Sequence[str | pathlib.Path], *, xmlparser: lxml.etree.XMLParser | None = None) -> lxml.etree._ElementTree
   :async:


   Asynchronously create a stitch file from a list of XML files.

   :param xmlfiles: A sequence of XML file paths to stitch together.
   :param xmlparser: An optional XML parser to use.
   :return: all XML file stitched together into a
       :class:`lxml.etree.ElementTree` object.


