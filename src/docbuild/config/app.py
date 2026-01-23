"""Application configuration handling."""

import re
from typing import Any

MAX_RECURSION_DEPTH: int = 10
"""The maximum recursion depth for placeholder replacement."""

type ConfigValue = (
    str | int | float | bool | list["ConfigValue"] | dict[str, "ConfigValue"]
)
"""A recursive type for values found in the configuration."""


class PlaceholderResolutionError(KeyError):
    """Exception raised when a placeholder cannot be resolved."""

    pass


class CircularReferenceError(ValueError):
    """Circular reference is detected in placeholder resolution."""

    pass


class PlaceholderResolver:
    """Handles placeholder resolution in configuration data."""

    PLACEHOLDER_PATTERN: re.Pattern[str] = re.compile(r"(?<!\{)\{([^{}]+)\}(?!\})")
    """Compiled regex for standard placeholders in configuration
       files (like ``{placeholder}``)."""

    def __init__(
        self, config: dict[str, Any], max_recursion_depth: int = MAX_RECURSION_DEPTH
    ) -> None:
        self.config = config
        self.max_recursion_depth = max_recursion_depth
        self._current_container: dict[str, Any] | list[Any] | None = None
        self._current_key: str | int | None = None

    def _resolve_dotted_path(self, path: str) -> ConfigValue:
        """Resolve a dotted path like 'paths.tmp.session'."""
        parts = path.split(".")
        value = self.config
        resolved_path = []
        container_name = self._get_container_name()

        for part in parts:
            resolved_path.append(part)
            if not isinstance(value, dict):
                full_path = ".".join(resolved_path)
                raise PlaceholderResolutionError(
                    f"While resolving '{{{path}}}' in '{container_name}': "
                    f"'{full_path}' is not a dictionary "
                    f"(got type {type(value).__name__}).",
                )
            if part not in value:
                full_path = ".".join(resolved_path)
                raise PlaceholderResolutionError(
                    f"While resolving '{{{path}}}' in '{container_name}': "
                    f"missing key '{part}' in path '{full_path}'.",
                )
            value = value[part]

        return value

    def _resolve_placeholder(self, match: re.Match) -> str:
        """Resolve a single placeholder match."""
        placeholder = match.group(1)
        container_name = self._get_container_name()

        if "." in placeholder:
            # Dotted path - resolve from root config
            return str(self._resolve_dotted_path(placeholder))
        elif (
            isinstance(self._current_container, dict)
            and placeholder in self._current_container
        ):
            # Simple key - resolve from current container
            return str(self._current_container[placeholder])
        else:
            # Key not found in current section
            raise PlaceholderResolutionError(
                f"While resolving '{{{placeholder}}}' in '{container_name}': "
                f"key '{placeholder}' not found in current section.",
            )

    def _resolve_string_placeholders(self, text: str) -> str:
        """Resolve all placeholders in a string with recursion protection."""
        count = 0
        cls = self.__class__
        while count < self.max_recursion_depth:
            new_text = cls.PLACEHOLDER_PATTERN.sub(self._resolve_placeholder, text)

            if new_text == text:
                # No more changes, we're done
                break

            text = new_text
            count += 1

        if count == self.max_recursion_depth:
            key_name = self._get_container_name()
            raise CircularReferenceError(
                f"Too many nested placeholder expansions in key '{key_name}'."
            )

        # Replace escaped braces with literal ones
        return text.replace("{{", "{").replace("}}", "}")

    def _get_container_name(self) -> str:
        """Get a human-readable name for the current container/key being processed."""
        if self._current_key is None:
            return "unknown"
        return (
            str(self._current_key)
            if isinstance(self._current_key, str)
            else f"list item at index {self._current_key}"
        )

    def get_container_name(self) -> str:
        """Public accessor for the current container/key name.

        This provides a stable, public way to retrieve the human-readable
        container name for diagnostics and tests without reaching into
        private attributes.
        """
        return self._get_container_name()

    def replace(self) -> dict[str, Any]:
        """Replace all placeholders in the configuration.

        :return: The configuration with all placeholders resolved.
        :raises PlaceholderResolutionError: If a placeholder cannot be resolved.
        :raises CircularReferenceError: If a circular reference is detected.
        """
        # Use a stack to process all items iteratively
        # Stack items: (container, key, context) where container can be dict or list
        stack: list[tuple[dict[str, Any] | list[Any], str | int, dict[str, Any]]] = [
            (self.config, key, self.config) for key in self.config
        ]

        while stack:
            container, key, context = stack.pop()

            # Set current context for private methods
            self._current_container = container
            self._current_key = key

            value = container[key]

            if isinstance(value, str):
                # Resolve placeholders in string values
                container[key] = self._resolve_string_placeholders(value)

            elif isinstance(value, dict):
                # Add all dict items to stack for processing
                for subkey in value:
                    stack.append((value, subkey, value))

            elif isinstance(value, list):
                # Add string/dict/list items from lists to stack for processing
                for i, item in enumerate(value):
                    if isinstance(item, dict | list | str):
                        stack.append((value, i, context))

        return self.config


def replace_placeholders(
    config: dict[str, Any] | None,
    max_recursion_depth: int = MAX_RECURSION_DEPTH,
) -> dict[str, Any] | None:
    """Replace placeholder values in a nested dictionary structure.

    * ``{foo}`` resolves from the current section.
    * ``{a.b.c}`` resolves deeply from the config.
    * ``{{foo}}`` escapes to literal ``{foo}``.

    :param config: The configuration dictionary.
    :param max_recursion_depth: Maximum recursion depth for placeholder resolution.
    :return: A new dictionary with placeholders replaced.
    :raises PlaceholderResolutionError: If a placeholder cannot be resolved.
    :raises CircularReferenceError: If a circular reference is detected.
    """
    if not isinstance(config, dict):
        return config

    resolver = PlaceholderResolver(config, max_recursion_depth)
    return resolver.replace()
