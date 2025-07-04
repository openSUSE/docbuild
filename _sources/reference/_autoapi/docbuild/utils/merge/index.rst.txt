docbuild.utils.merge
====================

.. py:module:: docbuild.utils.merge

.. autoapi-nested-parse::

   Utility functions for merging Doctype instances.



Functions
---------

.. autoapisummary::

   docbuild.utils.merge.merge_doctypes


Module Contents
---------------

.. py:function:: merge_doctypes(*doctypes: docbuild.models.doctype.Doctype) -> list[docbuild.models.doctype.Doctype]

   Merge a list of Doctype instances into a minimal set of non-redundant entries.

   Strategy:
       - For each incoming Doctype `dt`, compare it to the existing `result` list.
       - If any existing Doctype can absorb `dt`, extend its docset/langs as needed.
       - If `dt` can absorb an existing one, replace it.
       - Otherwise, keep both.
       - Wildcards ("*") are treated as "contains all" and will cause merging
         if overlap exists.
       - ``docset`` and ``langs`` are always sorted lists.

   Examples:
       - ``foo/1,2/en-us + foo/*/en-us`` => ``foo/*/en-us``
       - ``foo/1,2/* + foo/1/en-us`` => ``foo/1,2/*``
       - ``foo/1,2/en-us + bar/1,2/en-us`` => ``foo/1,2/en-us, bar/1,2/en-us``
       - ``foo/1/en-us + foo/2/*`` => ``foo/1/en-us', 'foo/2/*``
       - ``foo/1/en-us,de-de + foo/2/*`` => ``foo/1/en-us,de-de, foo/2/*``



