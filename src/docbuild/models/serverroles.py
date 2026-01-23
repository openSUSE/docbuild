from enum import StrEnum
from typing import Any, Self, cast

class ServerRole(StrEnum):
    """The server role."""

    PRODUCTION = 'production'
    STAGING = 'staging'
    TESTING = 'testing'

    @classmethod
    def _missing_(cls, value: object) -> Any: # Use Any here to satisfy the Enum metaclass requirements
        if not isinstance(value, str):
            return None
        
        v = value.lower()
        
        # Comprehensive alias map
        # We use 'cls' to access the members to ensure they are the correct type
        aliases: dict[str, ServerRole] = {
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
            return cast(Self, aliases[v])
        
        # Check if the string matches a member name (e.g., "PROD")
        for member in cls:
            if member.name.lower() == v:
                return cast(Self, member)
                
        return None