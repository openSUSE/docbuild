"""Custom Pydantic path types for robust configuration validation."""

import os
from pathlib import Path
from typing import Annotated

from pydantic import AfterValidator


def ensure_writeable_directory(path: Path) -> Path:
    """Validate a path is a writable directory, creating it if needed.

    Behavior:

    1. Expands user paths (e.g., ``~/data`` -> ``/home/user/data``).
    2. If path DOES NOT exist: It creates it (including parents) after
       verifying the first existing parent is writable.
    3. If path DOES exist (or was just created): It checks if it's a
       directory and has R/W/X permissions.

    :param path: The path to validate.
    :type path: pathlib.Path
    :return: The fully resolved, validated `pathlib.Path` object.
    :rtype: pathlib.Path
    :raises ValueError: If validation fails at any step (permissions, type, etc.).
    """
    # Ensure user expansion happens before any filesystem operations
    path = path.expanduser()

    # 1. Existence and Creation Logic
    if not path.exists():
        # Find the first existing parent directory to check for write permissions.
        # For a path like '/a/b/c', path.parents is ('/a/b', '/a', '/').
        # We find the first one in that sequence that exists.
        parent = next((p for p in path.parents if p.exists()), path.root)

        if not os.access(parent, os.W_OK):
            raise ValueError(
                f"Cannot create directory '{path}'. "
                f"Permission denied: Parent directory '{parent}' is not writable."
            )

        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise ValueError(f"Failed to create directory '{path}': {e.strerror}") from e

    # 2. Type Check
    if not path.is_dir():
        raise ValueError(f"Path exists but is not a directory: '{path}'")

    # 3. Permission Checks (R/W/X)
    permissions = (
        ("READ", os.R_OK),
        ("WRITE", os.W_OK),
        ("EXECUTE", os.X_OK),
    )
    missing_perms = [
        name for name, mode in permissions if not os.access(path, mode)
    ]

    if missing_perms:
        raise ValueError(
            f"Insufficient permissions for directory '{path}'. "
            f"Missing: {', '.join(missing_perms)}"
        )
    return path.resolve()


WritablePath = Annotated[Path, AfterValidator(ensure_writeable_directory)]
"""A Pydantic custom type that ensures a directory exists and is writable.
The final validated type is a :py:class:`pathlib.Path` object.
"""
