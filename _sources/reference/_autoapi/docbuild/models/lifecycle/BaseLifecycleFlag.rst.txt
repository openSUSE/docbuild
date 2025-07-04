docbuild.models.lifecycle.BaseLifecycleFlag
===========================================

.. py:class:: docbuild.models.lifecycle.BaseLifecycleFlag(*args, **kwds)

   Bases: :py:obj:`enum.Flag`

   .. autoapi-inheritance-diagram:: docbuild.models.lifecycle.BaseLifecycleFlag
      :parts: 1


   Base class for LifecycleFlag.


   .. py:method:: from_str(value: str) -> BaseLifecycleFlag
      :classmethod:


      Convert a string to a LifecycleFlag object.

      The string accepts the values 'supported', 'beta', 'hidden',
      'unsupported', or a combination of them separated by a comma or pipe.
      Addtionally, the class knows the values "UNKNOWN" and "unknown".
      An empty string, "", is equivalent to "UNKNOWN".

      Examples:
      >>> LifecycleFlag.from_str("supported")
      <LifecycleFlag.supported: 2>
      >>> LifecycleFlag.from_str("supported|beta")
      <LifecycleFlag.supported|beta: 6>
      >>> LifecycleFlag.from_str("beta,supported|beta")
      <LifecycleFlag.supported|beta: 6>
      >>> LifecycleFlag.from_str("")
      <LifecycleFlag.unknown: 0>




   .. py:method:: __contains__(other: str | enum.Flag) -> bool

      Return True if self has at least one of same flags set as other.

      >>> "supported" in Lifecycle.beta
      False
      >>> "supported|beta" in Lifecycle.beta
      True


