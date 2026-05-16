docbuild.config.xml.xinclude
============================

.. py:module:: docbuild.config.xml.xinclude

.. autoapi-nested-parse::

   Resolve XInclude and preserve source file metadata on inserted nodes.

   Any XInclude element is replaced with the content of the included file,
   and the included nodes are tagged with an ``xml:base`` attribute containing
   the path to the included file relative to the root config file.

   This allows to identify the source file for any node in the final merged XML tree, which is essential for validation.

   Use :func:`~docbuild.config.xml.xinclude.parse_xml_with_xinclude_base` to
   parse XML files with XInclude support:

   .. code:: python

       tree = await await asyncio.to_thread(parse_xml_with_xinclude_base,
                                            "path/to/portal.xml")
       # Nodes from included files are tagged with xml:base



Attributes
----------

.. autoapisummary::

   docbuild.config.xml.xinclude.XML_BASE_ATTR
   docbuild.config.xml.xinclude.XINCLUDE_TAG


Functions
---------

.. autoapisummary::

   docbuild.config.xml.xinclude.as_relative_posix
   docbuild.config.xml.xinclude.xpointer_to_xpath
   docbuild.config.xml.xinclude.mark_source
   docbuild.config.xml.xinclude.replace_include_with_nodes
   docbuild.config.xml.xinclude.resolve_includes
   docbuild.config.xml.xinclude.parse_xml_with_xinclude_base


Module Contents
---------------

.. py:data:: XML_BASE_ATTR
   :value: '{http://www.w3.org/XML/1998/namespace}base'


   The fully qualified name of the ``xml:base`` attribute in Clark notation.


.. py:data:: XINCLUDE_TAG
   :value: '{http://www.w3.org/2001/XInclude}include'


   The fully qualified name of the ``xi:include`` element in Clark notation.


.. py:function:: as_relative_posix(path: pathlib.Path, root_dir: pathlib.Path) -> str

   Return ``path`` relative to ``root_dir`` when possible.


.. py:function:: xpointer_to_xpath(xpointer: str) -> str | None

   Extract XPath from ``xpointer(...)`` expressions.


.. py:function:: mark_source(nodes: list[lxml.etree._Element], source: str) -> list[lxml.etree._Element]

   Copy selected nodes and set their ``xml:base`` attribute.


.. py:function:: replace_include_with_nodes(include: lxml.etree._Element, nodes: list[lxml.etree._Element]) -> None

   Replace one ``xi:include`` element with one or more resolved nodes.


.. py:function:: resolve_includes(tree: lxml.etree._ElementTree, *, current_path: pathlib.Path, root_dir: pathlib.Path, active_stack: set[pathlib.Path]) -> None

   Resolve all ``xi:include`` elements in ``tree`` recursively.


.. py:function:: parse_xml_with_xinclude_base(filepath: pathlib.Path | str) -> lxml.etree._ElementTree

   Parse XML and resolve XIncludes while preserving include source paths.

   Nodes inserted from included files are stamped with ``xml:base`` so callers
   can report the originating source file after include expansion.

   :param filepath: Path to the root XML file.
   :returns: Parsed and include-resolved XML tree.


