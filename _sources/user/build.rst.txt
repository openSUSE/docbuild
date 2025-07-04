Building documentation
======================

The :command:`docbuild build` subcommand is used to build the documentation from source files. It processes the source files and generates the output in the specified format, such as HTML or PDF.

.. code-block:: shell
   :caption: Synopsis of :command:`docbuild build`

   docbuild build [OPTIONS] DOCTYPE [DOCTYPE ...]


The doctype syntax
------------------

It requires a set of so called "doctypes" to be passed as argument. A *doctype*
describes the document to be built. The general syntax for a doctype is:

.. code-block:: text
   :caption: Doctype syntax

   [PRODUCT]/[DOCSET][@LIFECYCLES]/LANGS

The fields in the doctype have the following meanings:

* **PRODUCT** (optional): The product name, such as ``sles``, ``smart`` etc.
  You can omit this field if the product is not relevant for the document or you can use ``*`` to match all products.
* **DOCSET** (optional): The docset, usually the version or release of a product such as ``15-SP6``, ``16-GA`` etc.
  You can omit this field if the docset is not relevant for the document or you can use ``*`` to match all docsets.
* **LIFECYCLES** (optional): The lifecycle of the document that can have the values of ``supported``, ``beta``, ``unsupported``, or ``hidden``.
  You can omit this field if the lifecycle is not relevant for the document or you can use ``*`` to match all lifecycles. If you specify multiple lifecycles, separate them with commas (e.g., ``supported,beta``).
* **LANGS** (optional): The language of the document, such as ``en-us``, ``de-de``, etc.
  You can omit this field if the language is not relevant for the document or you can use ``*`` to match all languages. If you specify multiple languages, separate them with commas (e.g., ``en-us,de-de``).


Some common examples of doctypes are:

* ``//en-us``: Matches all supported deliverables in English.
* ``sles/*/en-us``: Matches all SLES deliverables in English, regardless of the docset or lifecycle.
* ``sle-ha//@unsupported/en-us,de-de``: Matches all SLE-HA deliverables in English and German that are in the unsupported lifecycle, regardless of the docset.
* ``"*/@beta,supported/de-de"``: Matches all SLES deliverables in German that are in the beta or supported lifecycle, regardless of the product.


Minimal set of doctypes
-----------------------

The :command:`docbuild build` subcommand can take multiple doctypes as arguments, allowing you to build multiple documents at once.
The command tries to find overlaps in the specified doctypes and only builds the documents that match all specified criteria avoiding unnecessary rebuilds.

.. code-block:: text
   :caption: Minimal set of doctypes

   [1] sles/*/en-us + sles/15-SP6/en-us      => sles/*/en-us
   [2] sles/*/en-us + sles/15-SP6/de-de      => sles/*/en-us,sles/15-SP6/de-de
   [3] sles/15-SP6/en-us + sles/15-SP6/de-de => sles/15-SP6/en-us,de-de
