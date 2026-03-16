"""Merge multiple dictionaries into a new one without modifying inputs."""

from collections.abc import Mapping
from copy import deepcopy
from typing import Any


def deep_merge(*dcts: Mapping[str, Any]) -> dict[str, Any]:
    """Merge multiple dictionaries into a new one without modifying inputs.

    Make a deep copy of the first dictionary and then update the copy with the
    subsequent dictionaries:

    * If a key exists in both dictionaries and both values are Mappings,
      they will be merged iteratively.
    * If both values are lists or tuples, they will be concatenated.
    * If both values are sets, they will be unioned.
    * Otherwise (different types or primitive values), the value from the
      subsequent dictionary will overwrite the previous one.

    This means that the order of dictionaries matters. The first dictionary
    will be the base, and the subsequent dictionaries will update it.

    :param dcts: Sequence of dictionaries to merge.
    :return: A new dictionary containing the merged values
            (does not change the passed dictionaries).
    """
    if not dcts:
        return {}

    result = deepcopy(dict(dcts[0]))

    for src in dcts[1:]:
        stack: list[tuple[dict[str, Any], Mapping[str, Any]]] = [(result, src)]

        while stack:
            dest, current = stack.pop()

            for key, value in current.items():
                if key not in dest:
                    dest[key] = deepcopy(value)
                    continue

                existing = dest[key]

                # Mapping → merge deeper
                if isinstance(existing, Mapping) and isinstance(value, Mapping):
                    # Ensure we are working with a dict for the merge target
                    # This avoids nested specialized types if they support item assignment
                    if type(existing) is not dict:
                        existing = dict(existing)
                        dest[key] = existing
                    stack.append((existing, value))

                # Lists / tuples → concatenate
                elif (isinstance(existing, list) and isinstance(value, list)) or (
                    isinstance(existing, tuple) and isinstance(value, tuple)
                ):
                    dest[key] = existing + deepcopy(value)  # type: ignore[operator]

                # Sets → union
                elif isinstance(existing, set) and isinstance(value, set):
                    dest[key] = existing | deepcopy(value)

                # Fallback → overwrite
                else:
                    dest[key] = deepcopy(value)

    return result
