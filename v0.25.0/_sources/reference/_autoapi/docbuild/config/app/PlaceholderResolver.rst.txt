docbuild.config.app.PlaceholderResolver
=======================================

.. py:class:: docbuild.config.app.PlaceholderResolver(config: dict[str, Any], max_recursion_depth: int = MAX_RECURSION_DEPTH)

   Handles placeholder resolution in configuration data.


   .. py:attribute:: PLACEHOLDER_PATTERN
      :type:  re.Pattern[str]

      Compiled regex for standard placeholders in configuration
      files (like ``{placeholder}``).



   .. py:method:: validate_brace_syntax(text: str, original_text: str) -> None

      Validate that curly braces are balanced and properly ordered.



   .. py:method:: get_container_name() -> str

      Public accessor for the current container/key name.

      This provides a stable, public way to retrieve the human-readable
      container name for diagnostics and tests without reaching into
      private attributes.



   .. py:method:: replace() -> dict[str, Any]

      Replace all placeholders in the configuration.

      :return: The configuration with all placeholders resolved.
      :raises PlaceholderResolutionError: If a placeholder cannot be resolved.
      :raises CircularReferenceError: If a circular reference is detected.
      :raises PlaceholderSyntaxError: If a placeholder has invalid syntax.


