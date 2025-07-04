docbuild.utils.convert
======================

.. py:module:: docbuild.utils.convert

.. autoapi-nested-parse::

   Convert utility functions.



Functions
---------

.. autoapisummary::

   docbuild.utils.convert.convert2bool


Module Contents
---------------

.. py:function:: convert2bool(value: str | bool) -> bool

   Convert a string or bool into a boolean.

   :param value: The value to convert to a boolean. Valid values are:

       * True, "yes", "true", "1", "on" for True and
       * False, "no", "false", "0", "off" for False.
   :return: The boolean value
   :raises ValueError: If the value cannot be converted to a valid boolean


