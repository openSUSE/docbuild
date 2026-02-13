"""Server roles for the docbuild application."""

from enum import StrEnum
from typing import Self


class ServerRole(StrEnum):
    """The server role.

    This Enum supports various aliases and case variations for each role.
    """

    # Primary Members
    PRODUCTION = "production"
    """The role for production environments.
    Aliases include 'prod', 'p', and any case variations."""

    STAGING = "staging"
    """The role for staging environments.
    Aliases include 'stage', 's', and any case variations."""

    TESTING = "testing"
    """The role for testing and developing.
    Aliases include 'test', 't', 'devel', 'dev', and any case variations."""

    #: Aliases for PRODUCTION
    PROD = "production"
    P = "production"
    prod = "production"
    p = "production"

    # Aliases for STAGING
    STAGE = "staging"
    S = "staging"
    stage = "staging"
    s = "staging"

    # Aliases for TESTING
    TEST = "testing"
    T = "testing"
    test = "testing"
    t = "testing"
    DEVEL = "testing"
    devel = "testing"
    DEV = "testing"
    dev = "testing"

    @classmethod
    def _missing_(cls: type[Self], value: object) -> "ServerRole | None":
        """Handle aliases and case-insensitive lookups using class members.

        If the value passed isn't a valid value (for example, 'production'),
        check if it matches one of the alias names (for example, 'p').
        """
        # Convert the input to a string to check against member keys
        name = str(value)
        member = cls.__members__.get(name)

        if member is not None:
            return member

        # If no match is found, raise ValueError with all valid names/aliases
        valid = ", ".join(cls.__members__.keys())
        raise ValueError(
            f"{name!r} is not a valid {cls.__name__}; valid names/aliases: {valid}"
        )
