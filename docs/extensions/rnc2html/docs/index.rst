RNC to HTML Extension
=====================

The ``rnc2html`` extension allows you to generate HTML documentation directly from RELAX NG schemas. It supports both RELAX NG Compact Syntax (``.rnc``) and XML Syntax (``.rng``).

For ``.rnc`` files, the extension automatically converts them to XML using the ``trang`` command-line tool before processing.

Features
--------

- **Automatic Conversion**: Converts RNC to RNG on the fly.
- **Documentation Extraction**: Extracts documentation from ``<db:refpurpose>`` (DocBook 5) annotations.
- **Structured Output**: Generates tables for attributes and lists for allowed child elements.
- **Content Models**: Displays regex-like content models (e.g., ``(title, para+)``).
- **Multi-page Support**: Can generate separate pages for every defined element.

Configuration
-------------

In your ``conf.py``:

.. code-block:: python

   extensions = [
       "rnc2html",
   ]

   # List of schemas to document (relative to source directory)
   rnc_html_files = [
       "schemas/myschema.rnc",
   ]

   # Generate a separate page for each element?
   rnc_html_multi_page = True

Example Schema (RNG)
--------------------

The extension looks for ``db:refpurpose`` elements in the ``http://docbook.org/ns/docbook`` namespace.

.. Comment 1
    **File: book.rng**

.. Comment 2
    .. literalinclude:: book.rng
      :language: xml
      :caption: Example RNG Schema with Annotations

Usage in RST
------------

You can also use the directive manually in any RST file:

.. code-block:: rst

   .. rnc-reference:: product-config-schema.rng

This will render the documentation for the schema in-place.


.. toctree::
   :maxdepth: 1
   :caption: Generated Reference

   reference/portal/index
