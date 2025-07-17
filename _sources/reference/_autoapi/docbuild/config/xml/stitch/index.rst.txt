docbuild.config.xml.stitch
==========================

.. py:module:: docbuild.config.xml.stitch

.. autoapi-nested-parse::

   Stitch file handling.



Functions
---------

.. autoapisummary::

   docbuild.config.xml.stitch.load_check_functions
   docbuild.config.xml.stitch.check_stitchfile
   docbuild.config.xml.stitch.create_stitchfile


Module Contents
---------------

.. py:function:: load_check_functions() -> list[collections.abc.Callable]

   Load all check functions from :mod:`docbuild.config.xml.checks`.


.. py:function:: check_stitchfile(tree: lxml.etree._Element | lxml.etree._ElementTree) -> bool

   Check the stitchfile for unresolved references.

   :param tree: The tree of the stitched XML file.
   :returns: True if no unresolved references are found, False otherwise.


.. py:function:: create_stitchfile(xmlfiles: collections.abc.Sequence[str | pathlib.Path], *, xmlparser: lxml.etree.XMLParser | None = None, with_ref_check: bool = True) -> lxml.etree._ElementTree
   :async:


   Asynchronously create a stitch file from a list of XML files.

   :param xmlfiles: A sequence of XML file paths to stitch together.
   :param xmlparser: An optional XML parser to use.
   :param with_ref_check: Whether to perform a reference check (=True) or not (=False).
   :return: all XML file stitched together into a
       :class:`lxml.etree.ElementTree` object.


