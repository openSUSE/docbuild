docbuild.config.app
===================

.. py:module:: docbuild.config.app

.. autoapi-nested-parse::

   Application configuration handling.



Attributes
----------

.. autoapisummary::

   docbuild.config.app.MAX_RECURSION_DEPTH
   docbuild.config.app.ConfigValue


Exceptions
----------

.. toctree::
   :hidden:

   /reference/_autoapi/docbuild/config/app/PlaceholderResolutionError
   /reference/_autoapi/docbuild/config/app/CircularReferenceError

.. autoapisummary::

   docbuild.config.app.PlaceholderResolutionError
   docbuild.config.app.CircularReferenceError


Classes
-------

.. toctree::
   :hidden:

   /reference/_autoapi/docbuild/config/app/PlaceholderResolver

.. autoapisummary::

   docbuild.config.app.PlaceholderResolver


Functions
---------

.. autoapisummary::

   docbuild.config.app.replace_placeholders


Module Contents
---------------

.. py:data:: MAX_RECURSION_DEPTH
   :type:  int
   :value: 10


   The maximum recursion depth for placeholder replacement.


.. py:type:: ConfigValue
   :canonical: str | int | float | bool | list['ConfigValue'] | dict[str, 'ConfigValue']


   A recursive type for values found in the configuration.


.. py:function:: replace_placeholders(config: dict[str, Any] | None, max_recursion_depth: int = MAX_RECURSION_DEPTH) -> dict[str, Any] | None

   Replace placeholder values in a nested dictionary structure.

   * ``{foo}`` resolves from the current section.
   * ``{a.b.c}`` resolves deeply from the config.
   * ``{{foo}}`` escapes to literal ``{foo}``.

   :param config: The configuration dictionary.
   :param max_recursion_depth: Maximum recursion depth for placeholder resolution.
   :return: A new dictionary with placeholders replaced.
   :raises PlaceholderResolutionError: If a placeholder cannot be resolved.
   :raises CircularReferenceError: If a circular reference is detected.


