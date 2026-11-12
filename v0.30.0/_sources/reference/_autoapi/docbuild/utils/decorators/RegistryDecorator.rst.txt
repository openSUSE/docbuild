docbuild.utils.decorators.RegistryDecorator
===========================================

.. py:class:: docbuild.utils.decorators.RegistryDecorator

   A class to register functions in a registry for XML checks.


   .. py:method:: __call__(func: F) -> F

      Register a function as a check.

      The method wraps the function unchanged, allowing it to be called
      with XML elements or trees.

      :param func: The function to register.
      :return: The wrapped function.


