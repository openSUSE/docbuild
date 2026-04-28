"""Utility to flatten nested dictionaries into dotted keys."""

from collections.abc import Generator
from typing import Any


def flatten_dict(d: dict[str, Any], prefix: str = "") -> Generator[tuple[str, Any], None, None]:
    """Recursively flatten a nested dictionary into dotted keys.

    :param d: The dictionary to flatten.
    :param prefix: The current key prefix (used for recursion).
    :yields: Tuples of (dotted_key, value).
    """
    for k, v in d.items():
        new_key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            yield from flatten_dict(v, new_key)
        else:
            yield new_key, v
