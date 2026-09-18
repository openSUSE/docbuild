docbuild.config.xml.list
========================

.. py:module:: docbuild.config.xml.list

.. autoapi-nested-parse::

   List all deliverables from the stitched Docserv config.



Functions
---------

.. autoapisummary::

   docbuild.config.xml.list.list_all_deliverables


Module Contents
---------------

.. py:function:: list_all_deliverables(tree: lxml.etree._Element | lxml.etree._ElementTree, doctypes: collections.abc.Sequence[docbuild.models.doctype.Doctype] | None = None) -> collections.abc.Generator[lxml.etree._Element, None, None]

   Generate to list all deliverables from the stitched Docserv config.

   :param tree: the XML tree from the stitched Docserv config
   :param doctypes: a sequence of :class:`~docbuild.models.doctype.Doctype` objects.
   :yield: the ``<deliverable>`` node that matches the criteria


