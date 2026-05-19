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

.. py:function:: deep_merge(*dcts: collections.abc.Mapping[str, Any]) -> dict[str, Any]

   Merge multiple dictionaries into a new one without modifying inputs.

   Make a deep copy of the first dictionary and then update the copy with the
   subsequent dictionaries:

   * If a key exists in both dictionaries and both values are Mappings,
     they will be merged iteratively.
   * If both values are lists or tuples, they will be concatenated.
   * If both values are sets, they will be unioned.
   * Otherwise (different types or primitive values), the value from the
     subsequent dictionary will overwrite the previous one.

   This means that the order of dictionaries matters. The first dictionary
   will be the base, and the subsequent dictionaries will update it.

   :param dcts: Sequence of dictionaries to merge.
   :return: A new dictionary containing the merged values
           (does not change the passed dictionaries).


