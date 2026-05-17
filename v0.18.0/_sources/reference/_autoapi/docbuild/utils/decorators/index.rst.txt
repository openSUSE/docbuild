docbuild.utils.decorators
=========================

.. py:module:: docbuild.utils.decorators

.. autoapi-nested-parse::

   Useful decorators for XML checks.



Attributes
----------

.. autoapisummary::

   docbuild.utils.decorators.F


Classes
-------

.. toctree::
   :hidden:

   /reference/_autoapi/docbuild/utils/decorators/RegistryDecorator

.. autoapisummary::

   docbuild.utils.decorators.RegistryDecorator


Functions
---------

.. autoapisummary::

   docbuild.utils.decorators.factory_registry


Module Contents
---------------

.. py:data:: F

   A type variable representing a callable that takes an XML element or tree


.. py:function:: factory_registry() -> collections.abc.Callable[[F], F]

   Create a decorator that registers functions in its own registry.

   Example usage:

   >>> register_check = factory_registry()
   >>> @register_check
   ... def check_example(tree: etree._Element | etree._ElementTree) -> bool:
   ...     return True
   >>> register_check.registry[0].__name__
   'check_example'

   :return: A decorator that registers functions in a registry,
      see :class:`~docbuild.utils.decorators.RegistryDecorator`.


