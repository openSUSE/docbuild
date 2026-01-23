"""Custom Pydantic path types for robust configuration validation."""

import os
from pathlib import Path
from typing import Self

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema


class EnsureWritableDirectory:
    """A Pydantic custom type that ensures a directory exists and is writable.

    Behavior:
    1. Expands user paths (e.g., "~/data" -> "/home/user/data").
    2. Validates input is a path.
    3. If path DOES NOT exist: It creates it (including parents).
    4. If path DOES exist (or was just created): It checks is_dir()
       and R/W/X permissions.
    """

    def __init__(self, path: str | Path) -> None:
        """Initialize the instance with the fully resolved and expanded path.

        Assumes the validation step (validate_and_create) has already handled
        creation and permission checks.
        """
        self._path: Path = Path(path).expanduser().resolve()

    # --- Pydantic V2 Core Schema ---

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: type[Path], handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        """Define Validation AND Serialization logic."""
        # 1. Validation Logic (The Chain)
        validation_schema = core_schema.chain_schema(
            [
                handler(Path),
                core_schema.no_info_plain_validator_function(cls.validate_and_create),
            ]
        )
        # 2. Serialization Logic (Convert to String)
        # This tells Pydantic: "When dumping to JSON or Python, use str(instance)"
        serialization_schema = core_schema.plain_serializer_function_ser_schema(
            lambda instance: str(instance),
            when_used="always",  # Apply to both JSON and Python (dict) dumps
        )
        # 3. Combine Validation and Serialization
        return core_schema.json_or_python_schema(
            json_schema=validation_schema,
            python_schema=validation_schema,
            serialization=serialization_schema,
        )

    # --- Validation & Creation Logic ---

    @classmethod
    def validate_and_create(cls, path: Path) -> Self:
        """Expand user, checks if path exists.

        If not, creates it. Then checks permissions.
        """
        # Ensure user expansion happens before any filesystem operations
        path = path.expanduser()

        # 1. Auto-Creation Logic
        if not path.exists():
            try:
                # parents=True: creates /tmp/a/b even if /tmp/a doesn't exist
                # exist_ok=True: prevents race conditions
                path.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                raise ValueError(f"Could not create directory '{path}': {e}") from e

        # 2. Type Check
        if not path.is_dir():
            raise ValueError(f"Path exists but is not a directory: '{path}'")

        # 3. Permission Checks (R/W/X)
        missing_perms = []
        if not os.access(path, os.R_OK):
            missing_perms.append("READ")
        if not os.access(path, os.W_OK):
            missing_perms.append("WRITE")
        if not os.access(path, os.X_OK):
            missing_perms.append("EXECUTE")

        if missing_perms:
            raise ValueError(
                f"Insufficient permissions for directory '{path}'. "
                f"Missing: {', '.join(missing_perms)}"
            )

        # Return an instance of the custom type (the __init__ method runs next)
        return cls(path)

    # --- Usability Methods ---
    def __str__(self) -> str:
        """Return the string representation of the path."""
        return str(self._path)

    def __repr__(self) -> str:
        """Return the developer-friendly representation of the object."""
        return f"{self.__class__.__name__}('{self._path}')"

    def __truediv__(self, other: str) -> Path:
        """Implement the / operator to delegate to the underlying Path object."""
        return self._path / other

    # Allows access to methods/attributes of the underlying Path object
    # (e.g., .joinpath)
    def __getattr__(self, name: str) -> object:
        """Delegate attribute access to the underlying Path object."""
        return getattr(self._path, name)

    def __fspath__(self) -> str:
        """Return the string path for os.PathLike compatibility."""
        return str(self._path)
