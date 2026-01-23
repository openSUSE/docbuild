"""Server roles for the docbuild application."""

from enum import StrEnum
from typing import Self


class ServerRole(StrEnum):
    """The server role."""

    PRODUCTION = "production"
    STAGING = "staging"
    TESTING = "testing"

    @classmethod
    def _missing_(cls, value: object) -> str | None:
        """Handle aliases and case-insensitive lookups."""
        if not isinstance(value, str):
            return None

        v = value.lower()

        # Comprehensive alias map
        aliases: dict[str, str] = {
            "p": cls.PRODUCTION,
            "prod": cls.PRODUCTION,
            "s": cls.STAGING,
            "stage": cls.STAGING,
            "t": cls.TESTING,
            "test": cls.TESTING,
            "devel": cls.TESTING,
            "dev": cls.TESTING,
        }

        if v in aliases:
            return aliases[v]

        # Check if the string matches a member name (e.g., "PROD")
        for member in cls:
            if member.name.lower() == v:
                return member

        return None