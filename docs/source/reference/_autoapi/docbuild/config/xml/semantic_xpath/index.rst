docbuild.config.xml.semantic_xpath
==================================

.. py:module:: docbuild.config.xml.semantic_xpath

.. autoapi-nested-parse::

   Build readable, semantic XPath expressions for XML nodes.

   The helper in this module prefers stable attribute-based predicates like
   ``@id`` and ``@lang`` where possible and falls back to positional predicates
   for ambiguous siblings.



Functions
---------

.. autoapisummary::

   docbuild.config.xml.semantic_xpath.xpath_literal
   docbuild.config.xml.semantic_xpath.position_among_same_tag_siblings
   docbuild.config.xml.semantic_xpath.is_unique_among_same_tag_siblings
   docbuild.config.xml.semantic_xpath.preferred_predicate_attributes
   docbuild.config.xml.semantic_xpath.semantic_xpath


Module Contents
---------------

.. py:function:: xpath_literal(value: str) -> str

   Return ``value`` as a safely escaped XPath string literal.

   :param value: Arbitrary text value that will be embedded in an XPath predicate.
   :returns: A valid XPath literal expression.


.. py:function:: position_among_same_tag_siblings(node: lxml.etree._Element) -> int

   Return the 1-based position among same-tag siblings.

   :param node: Node whose sibling position should be computed.
   :returns: Position among siblings with the same element name.


.. py:function:: is_unique_among_same_tag_siblings(node: lxml.etree._Element, attr: str, value: str) -> bool

   Return whether ``attr=value`` uniquely identifies ``node`` among siblings.

   :param node: Node to validate.
   :param attr: Attribute name to test.
   :param value: Attribute value to test.
   :returns: ``True`` if no sibling with same tag shares ``attr=value``.


.. py:function:: preferred_predicate_attributes(node_name: str) -> tuple[str, Ellipsis]

   Return preferred attribute keys for semantic predicates.

   :param node_name: XML element local name.
   :returns: Ordered attribute names to try for predicate generation.


.. py:function:: semantic_xpath(node: lxml.etree._Element) -> str

   Build a readable absolute XPath for ``node``.

   The function prefers stable attribute predicates where possible and falls
   back to positional predicates when attributes are missing or ambiguous.

   :param node: Target XML element.
   :returns: Absolute XPath expression for the provided node.


