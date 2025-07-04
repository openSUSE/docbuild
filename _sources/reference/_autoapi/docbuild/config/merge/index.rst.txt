docbuild.config.merge
=====================

.. py:module:: docbuild.config.merge

.. autoapi-nested-parse::

   Merge multiple dictionaries into a new one without modifying inputs.



Functions
---------

.. autoapisummary::

   docbuild.config.merge.deep_merge


Module Contents
---------------

.. py:function:: deep_merge(*dcts: dict[str, Any]) -> dict[str, Any]

   Merge multiple dictionaries into a new one without modifying inputs.

   Make a deep copy of the first dictionary and then update the copy with the
   subsequent dictionaries:

   * If a key exists in both dictionaries, the value from the last dictionary
     will overwrite the previous one.
   * If the value is a list, it will concatenate the lists.
   * If the value is a primitive type, it will overwrite the value.
   * If a key exists in multiple dictionaries, the last one will take precedence.

   This means that the order of dictionaries matters. The first dictionary
   will be the base, and the subsequent dictionaries will update it.

   :param dcts: Sequence of dictionaries to merge.
   :return: A new dictionary containing the merged values
           (does not change the passed dictionaries).


