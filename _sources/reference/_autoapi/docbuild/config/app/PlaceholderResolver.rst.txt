docbuild.config.app.PlaceholderResolver
=======================================

.. py:class:: docbuild.config.app.PlaceholderResolver(config: dict[str, Any], max_recursion_depth: int = MAX_RECURSION_DEPTH)

   Handles placeholder resolution in configuration data.


   .. py:attribute:: PLACEHOLDER_PATTERN
      :type:  re.Pattern[str]

      Compiled regex for standard placeholders in configuration
      files (like ``{placeholder}``).



   .. py:method:: replace() -> dict[str, Any]

      Replace all placeholders in the configuration.

      :return: The configuration with all placeholders resolved.
      :raises PlaceholderResolutionError: If a placeholder cannot be resolved.
      :raises CircularReferenceError: If a circular reference is detected.


