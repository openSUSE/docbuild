"""Utility functions for data manipulation."""

from collections.abc import Generator
from typing import Any


def flatten_dict(d: dict[str, Any], prefix: str = "") -> Generator[tuple[str, Any], None, None]:
    """Yield flattened key-value pairs from a nested dictionary.

    :param d: The dictionary to flatten.
    :param prefix: The accumulated path of keys.
    :yields: A tuple containing (dotted_key, value).
    """
    for k, v in d.items():
        new_key = f"{prefix}.{k}" if prefix else k

        if isinstance(v, dict):
            yield from flatten_dict(v, new_key)
        else:
            yield new_key, v
