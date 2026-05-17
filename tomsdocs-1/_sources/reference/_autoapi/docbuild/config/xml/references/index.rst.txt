docbuild.config.xml.references
==============================

.. py:module:: docbuild.config.xml.references

.. autoapi-nested-parse::

   Check <ref/> links on a stitched XML configuration file.



Functions
---------

.. autoapisummary::

   docbuild.config.xml.references.check_ref_to_subdeliverable
   docbuild.config.xml.references.check_ref_to_deliverable
   docbuild.config.xml.references.check_ref_to_link
   docbuild.config.xml.references.check_ref_to_docset
   docbuild.config.xml.references.check_ref_to_product
   docbuild.config.xml.references.check_stitched_references


Module Contents
---------------

.. py:function:: check_ref_to_subdeliverable(ref: lxml.etree._Element, attrs: dict[str, str]) -> str | None

   Check reference to a subdeliverable.


.. py:function:: check_ref_to_deliverable(ref: lxml.etree._Element, attrs: dict[str, str]) -> str | None

   Check reference to a deliverable.


.. py:function:: check_ref_to_link(ref: lxml.etree._Element, attrs: dict[str, str]) -> str | None

   Check ref to an external link.


.. py:function:: check_ref_to_docset(ref: lxml.etree._Element, attrs: dict[str, str]) -> str | None

   Check reference to a docset.


.. py:function:: check_ref_to_product(ref: lxml.etree._Element, attrs: dict[str, str]) -> str | None

   Check reference to a product.


.. py:function:: check_stitched_references(tree: lxml.etree._ElementTree) -> list[str]

   Check <ref> elements for broken references.

   This function is a Python equivalent of the
   ``global-check-ref-list.xsl`` stylesheet.

   :param tree: The tree of the stitched XML file.
   :returns: A list of error messages for any broken references found.


