docbuild.models.lifecycle.LifecycleFlag
=======================================

.. py:class:: docbuild.models.lifecycle.LifecycleFlag(*args, **kwds)

   Bases: :py:obj:`enum.Flag`

   .. autoapi-inheritance-diagram:: docbuild.models.lifecycle.LifecycleFlag
      :parts: 1


   LifecycleFlag represents the lifecycle of a product.


   .. py:attribute:: unknown
      :value: 0


      Unknown lifecycle state.



   .. py:attribute:: supported

      Supported lifecycle state.



   .. py:attribute:: beta

      Beta lifecycle state.



   .. py:attribute:: hidden

      Hidden lifecycle state.



   .. py:attribute:: unsupported

      Unsupported lifecycle state.



   .. py:method:: from_str(value: str) -> LifecycleFlag
      :classmethod:


      Convert a string to a LifecycleFlag object.

      The string accepts the values 'supported', 'beta', 'hidden',
      'unsupported', or a combination of them separated by a comma or pipe.
      Additionally, the class knows the values "unknown".
      An empty string, "", is equivalent to "unknown".

      Examples:
      >>> LifecycleFlag.from_str("supported")
      <LifecycleFlag.supported: 2>
      >>> LifecycleFlag.from_str("supported,beta")
      <LifecycleFlag.supported|beta: 6>
      >>> LifecycleFlag.from_str("beta,supported|beta")
      <LifecycleFlag.supported|beta: 6>
      >>> LifecycleFlag.from_str("")
      <LifecycleFlag.unknown: 0>




   .. py:method:: __contains__(other: str | enum.Flag) -> bool

      Return True if self has at least one of same flags set as other.

      >>> "supported" in LifecycleFlag.beta
      False
      >>> "supported|beta" in LifecycleFlag.beta
      True


