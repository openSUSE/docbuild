"""Application configuration handling."""

import re
from typing import Any

from ..constants import ESCAPE_REGEX

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


class PlaceholderSyntaxError(ValueError):
    """Exception raised when a placeholder has invalid syntax."""

    pass

def unescape(text: str, keep_runtime: bool) -> str:
    """Unescape double curly braces, optionally preserving runtime placeholders.

    :param text: The text to unescape.
    :param keep_runtime: If True, keep escaped runtime placeholders like
        ``{{product}}`` as they are.
    :return: The unescaped text.

    For example:

    .. code-block:: python

        >>> unescape("{{foo}} and {{product}}", keep_runtime=False)
        '{foo} and {product}'
        >>> unescape("{{foo}} and {{product}}", keep_runtime=True)
        '{foo} and {{product}}'
    """
    if not keep_runtime:
        return text.replace("{{", "{").replace("}}", "}")

    return ESCAPE_REGEX.sub(
        lambda m: m.group(0) if m.group("runtime") else m.group(0)[0], text
    )


def normalize_runtime_placeholders(text: str) -> str:
    """Convert supported escaped runtime placeholders for ``str.format``.

    Other escaped braces are kept as they are.

    :param text: The text with escaped runtime placeholders.
    :return: The text with ``{{name}}`` turned into ``{name}`` for
        each runtime placeholder.

    For example:

    .. code-block:: python

        >>> normalize_runtime_placeholders("{{product}}/{{docset}}/{{foo}}")
        '{product}/{docset}/{{foo}}'
    """
    return ESCAPE_REGEX.sub(
        lambda match: (
            f"{{{match.group('runtime')}}}"
            if match.group("runtime")
            else match.group(0)
        ),
        text,
    )


class PlaceholderResolver:
    """Handles placeholder resolution in configuration data."""

    PLACEHOLDER_PATTERN: re.Pattern[str] = re.compile(r"(?<!\{)\{([^{}]+)\}(?!\})")
    """Compiled regex for standard placeholders in configuration
       files (like ``{placeholder}``)."""

    def __init__(
        self, config: dict[str, Any], max_recursion_depth: int = MAX_RECURSION_DEPTH, *, keep_runtime: bool = False
    ) -> None:
        """Initialize the resolver.

        :param config: The configuration dictionary. It is changed in place.
        :param max_recursion_depth: Maximum number of nested placeholder
            expansions for one value.
        :param keep_runtime: If True, keep escaped runtime placeholders like
            ``{{product}}`` as they are.
        """
        self.config = config
        self.max_recursion_depth = max_recursion_depth
        self.keep_runtime: bool = keep_runtime
        self._current_container: dict[str, Any] | list[Any] | None = None
        self._current_key: str | int | None = None

    def _resolve_dotted_path(self, path: str) -> ConfigValue:
        """Resolve a dotted path like 'paths.tmp.session'.

        :param path: The dotted path, resolved from the root of the config.
        :return: The value at the end of the path.
        :raises PlaceholderResolutionError: If a key is missing or a part
            of the path is not a dictionary.
        """
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
        """Resolve a single placeholder match.

        :param match: The regex match of a placeholder like ``{foo}``.
        :return: The resolved value as a string.
        :raises PlaceholderResolutionError: If the placeholder cannot be
            resolved.
        """
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

    def validate_brace_syntax(self, text: str, original_text: str) -> None:
        """Validate that curly braces are balanced and properly ordered.

        :param text: The text to check, after placeholders were resolved.
        :param original_text: The original value, used in the error message.
        :raises PlaceholderSyntaxError: If the braces are not balanced or
            a ``}`` comes before a ``{``.
        """
        brace_level = 0
        for char in text:
            if char == "{":
                brace_level += 1
            elif char == "}":
                brace_level -= 1

            # If it ever drops below 0, we've hit a '}' before a '{'
            if brace_level < 0:
                break

        # If the level isn't exactly 0 at the end, the syntax is broken
        if brace_level != 0:
            container_name = self._get_container_name()

            if "{" in text and "}" not in text:
                msg = f"Missing end curly brace in placeholder in value: '{original_text}'"
            elif "}" in text and "{" not in text:
                msg = f"Missing start curly brace in placeholder in value: '{original_text}'"
            else:
                msg = f"Invalid placeholder syntax in value: '{original_text}'"

            raise PlaceholderSyntaxError(f"In configuration key '{container_name}': {msg}")

    def _resolve_string_placeholders(self, text: str) -> str:
        """Resolve all placeholders in a string with recursion protection.

        :param text: The string with placeholders.
        :return: The string with all placeholders resolved.
        :raises CircularReferenceError: If there are too many nested
            placeholder expansions.
        :raises PlaceholderResolutionError: If a placeholder cannot be
            resolved.
        :raises PlaceholderSyntaxError: If a placeholder has invalid syntax.
        """
        original_text = text
        count = 0
        cls = self.__class__

        # 1. Resolve valid placeholders
        while count < self.max_recursion_depth:
            new_text = cls.PLACEHOLDER_PATTERN.sub(self._resolve_placeholder, text)
            if new_text == text:
                break
            text = new_text
            count += 1

        if count == self.max_recursion_depth:
            key_name = self._get_container_name()
            raise CircularReferenceError(
                f"Too many nested placeholder expansions in key '{key_name}'."
            )

        # 2. Syntax Validation using the helper method
        self.validate_brace_syntax(text, original_text)

        # 3. Final cleanup of escapes
        return unescape(text, self.keep_runtime)

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
        :raises PlaceholderSyntaxError: If a placeholder has invalid syntax.
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
    *,
    keep_runtime: bool = False,
) -> dict[str, Any] | None:
    """Replace placeholder values in a nested dictionary structure.

    * ``{foo}`` resolves from the current section.
    * ``{a.b.c}`` resolves deeply from the config.
    * ``{{foo}}`` escapes to literal ``{foo}``.

    :param config: The configuration dictionary.
    :param max_recursion_depth: Maximum recursion depth for placeholder resolution.
    :param keep_runtime: If True, keep escaped runtime placeholders like
        ``{{product}}`` as they are.
    :return: A new dictionary with placeholders replaced.
    :raises PlaceholderResolutionError: If a placeholder cannot be resolved.
    :raises CircularReferenceError: If a circular reference is detected.
    :raises PlaceholderSyntaxError: If a placeholder has invalid syntax.

    For example:

    .. code-block:: python

        >>> config = replace_placeholders({
        ...     "paths": {"root": "/data", "tmp": "{root}/tmp"},
        ...     "log": "{paths.root}/log",
        ...     "raw": "{{root}}",
        ... })
        >>> config["paths"]["tmp"]
        '/data/tmp'
        >>> config["log"]
        '/data/log'
        >>> config["raw"]
        '{root}'
    """
    if not isinstance(config, dict):
        return config

    resolver = PlaceholderResolver(config, max_recursion_depth, keep_runtime=keep_runtime)
    return resolver.replace()
