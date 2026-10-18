docbuild.utils.flatten
======================

.. py:module:: docbuild.utils.flatten

.. autoapi-nested-parse::

   Utility to flatten nested dictionaries into dotted keys.



Functions
---------

.. autoapisummary::

   docbuild.utils.flatten.flatten_dict


Module Contents
---------------

.. py:function:: flatten_dict(d: dict[str, Any], prefix: str = '') -> collections.abc.Generator[tuple[str, Any], None, None]

   Recursively flatten a nested dictionary into dotted keys.

   :param d: The dictionary to flatten.
   :param prefix: The current key prefix (used for recursion).
   :yields: Tuples of (dotted_key, value).


