"""Caching related classes."""

import dataclasses
import hashlib
import json
from pathlib import Path
from typing import Self


@dataclasses.dataclass(frozen=True)
class Cache:
    """Represent an immutable cache of source files and environment config."""

    env_config_hash: str
    file_hashes: dict[str, str] = dataclasses.field(default_factory=dict)

    @classmethod
    def from_json(cls, path: Path) -> Self:
        """Load the cache from a JSON file. Returns an empty cache on failure."""
        if not path.exists():
            return cls(env_config_hash="", file_hashes={})
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return cls(
                env_config_hash=data.get("env_config_hash", ""),
                file_hashes=data.get("dependencies", {})
            )
        except (json.JSONDecodeError, OSError):
            return cls(env_config_hash="", file_hashes={})

    def to_json(self, path: Path) -> None:
        """Save the cache to a JSON file."""
        data = {
            "env_config_hash": self.env_config_hash,
            "dependencies": self.file_hashes
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    @property
    def combined_hash(self) -> str:
        """A single hash representing the state of all files and the environment."""
        hasher = hashlib.sha256()
        hasher.update(self.env_config_hash.encode('utf-8'))

        # Sort items to guarantee consistent hashing regardless of dictionary order
        for _, file_hash in sorted(self.file_hashes.items()):
            hasher.update(file_hash.encode('utf-8'))

        return hasher.hexdigest()

    def files(self) -> set[str]:
        """Return a set of all relative file paths in the cache."""
        return set(self.file_hashes.keys())

    def diff(self, other: Self) -> set[str]:
        """Compare this cache with another.

        Returns a comprehensive set of all files that have been added,
        removed, or modified.
        """
        # Get added and removed files
        changed = self.files().symmetric_difference(other.files())

        # Check for modified files by comparing hashes of common files
        for path in self.files().intersection(other.files()):
            if self.file_hashes[path] != other.file_hashes[path]:
                changed.add(path)

        return changed
