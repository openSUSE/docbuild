docbuild.utils.doc
==================

.. py:module:: docbuild.utils.doc

.. autoapi-nested-parse::

   Utility decorators for docbuild.



Classes
-------

.. toctree::
   :hidden:

   /reference/_autoapi/docbuild/utils/doc/SafeDict

.. autoapisummary::

   docbuild.utils.doc.SafeDict


Functions
---------

.. autoapisummary::

   docbuild.utils.doc.docstring


Module Contents
---------------

.. py:function:: docstring(template: str | None = None, **kwargs: Any) -> collections.abc.Callable[[collections.abc.Callable[P, R]], collections.abc.Callable[P, R]]

   Replace placeholders in docstring.

   This decorator formats the docstring of the decorated function
   (or an explicit template string) by replacing placeholders
   with the provided keyword arguments. If a placeholder does not
   have a corresponding keyword argument, it will remain unchanged
   in the docstring.

   If `template` is None, the decorated function's existing docstring is used.
   Placeholders in the form `{key}` are replaced by corresponding keyword arguments.
   Missing keys remain unchanged in the docstring.

   :param template: Optional string template with placeholders.
       Defaults to the function's docstring if None.
   :param kwargs: Keyword arguments mapping placeholder names to their
       replacement values.
   :return: Decorated function with the updated docstring.

   :example:

   .. code-block:: python

       @docstring("Hello {name}, welcome to {place}", name="Alice")
       def greet():
           pass

       print(greet.__doc__)
       # Output: "Hello Alice, welcome to {place}"


