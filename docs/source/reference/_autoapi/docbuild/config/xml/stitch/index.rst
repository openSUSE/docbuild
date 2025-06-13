docbuild.config.xml.stitch
==========================

.. py:module:: docbuild.config.xml.stitch

.. autoapi-nested-parse::

   Stitch file handling.



Functions
---------

.. autoapisummary::

   docbuild.config.xml.stitch.load_check_functions
   docbuild.config.xml.stitch.validate_xmlconfig
   docbuild.config.xml.stitch.create_stitchfile


Module Contents
---------------

.. py:function:: load_check_functions() -> list[collections.abc.Callable]

   Load all check functions from :mod:`docbuild.config.xml.checks`.


.. py:function:: validate_xmlconfig(xmlfile: str | pathlib.Path, parser: lxml.etree.XMLParser | None = None) -> bool

   Validate an XML config file.

   :param xmlfile: The XML file to validate.
   :param xmlparser: An optional XML parser to use for validation.
   :return: the parsed :class:`lxml.etree.ElementTree` object.


.. py:function:: create_stitchfile(configdir: str | pathlib.Path, *, filepattern: str = '[a-zA-Z0-9]*.xml', xmlparser: lxml.etree.XMLParser | None = None) -> lxml.etree._ElementTree

   Create a stitch file from a config directory.

   :param configdir: The config directory to search for XML files.
   :param filepattern: A glob pattern that matches files in configdir.
   :return: the stitched :class:`lxml.etree.ElementTree` object.


