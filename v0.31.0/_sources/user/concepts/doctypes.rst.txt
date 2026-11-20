.. _concept-doctype-syntax:

The Doctype Syntax
==================

Docbuild requires for some subcommands so called "doctypes" to be passed as argument. A *doctype* (class :class:`~docbuild.models.doctype.Doctype`)
describes the documents that are going to be processed.

The general syntax for a doctype is:

.. code-block:: ebnf
   :caption: EBNF for the Doctype syntax
   :name: ebnf-doctype-syntax

   Doctype = ["/"] [PRODUCT] "/" [DOCSET {"," DOCSET}] ["@" LIFECYCLES] ["/" [LANGS]] ;


The fields in the doctype have the following meanings (without any slashes):

* **PRODUCT** (optional): The product name, such as ``sles``, ``smart`` etc.
  You can omit this field if the product is not relevant for the document or you can use ``*`` to match all products.
  The acronym is checked against a pre-defined set of products.
* **DOCSET** (optional): The docset, usually the version or release of a product such as ``15-SP6``, ``16-GA`` etc.
  You can omit this field if the docset is not relevant or you can use ``*`` to match all docsets.
  If you specify multiple docsets, separate them with commas (e.g., ``15-SP6,16-GA``).
* **LIFECYCLES** (optional): The lifecycle of the document that can have the values of ``supported``, ``beta``, ``unsupported``, or ``unpublished``.
  You can omit this field if the lifecycle is not relevant or you can use ``@*`` to match all lifecycles.
  If you specify multiple lifecycles, separate them with commas (e.g., ``@supported,beta``).
* **LANGS** (optional): The language of the document, such as ``en-us``, ``de-de``, etc.
  You can omit this field if the language is not relevant or you can use ``*`` to match all languages.
  If you leave this field empty, it will default to English (``en-us``).
  If you specify multiple languages, separate them with commas (e.g., ``en-us,de-de``).


Some common examples of doctypes are:

* ``sles/15-SP6/en-us`` or ``/sles/15-SP6/en-us``: Matches the English deliverables for SLES 15-SP6, regardless of the lifecycle.
* ``*/*/de-de``: Matches all deliverables in German, regardless of the product, docset, or lifecycle.
* ``//en-us``: Matches all deliverables in English, regardless of product, docset, or lifecycle. This is a shorter version of ``*/*/en-us``.
* ``/@supported/``: Matches all supported English deliverables, regardless of the product, docset.
* ``sles//en-us``: Matches all English SLES deliverables, regardless of the docset or lifecycle.
* ``sle-ha/@unsupported/en-us,de-de``: Matches all SLE-HA deliverables in English and German that are in the unsupported lifecycle, regardless of the docset.
* ``*/@beta,supported/de-de``: Matches all deliverables in German that are in the beta or supported lifecycle, regardless of the product or docset.
* ``//*``: Matches all deliverables in all languages, regardless of the product, docset, or lifecycle.
* ``//``: Matches all English deliverables, regardless of the product, docset, or lifecycle. Same as ``*/*/en-us`` or ``//en-us``.



Minimal Set of Doctypes
-----------------------

Docbuild can take multiple doctypes as arguments, allowing you to process multiple documents at once.
However, docbuild tries to find overlaps in the specified doctypes and only returns the documents that match all specified criteria avoiding unnecessary processing.

.. code-block:: text
   :caption: Minimal set of doctypes

   [1] sles/*/en-us + sles/15-SP6/en-us      => sles/*/en-us
   [2] sles/*/en-us + sles/15-SP6/de-de      => sles/*/en-us,sles/15-SP6/de-de
   [3] sles/15-SP6/en-us + sles/15-SP6/de-de => sles/15-SP6/en-us,de-de

Explanations:

1. An ``*`` as docset matches all docsets. A docset 15-SP6 is included.
2. This can't be reduced further, so it stays as it is.
3. Both products and docsets are the same, only the languages are different. These two sets are combined into one.
