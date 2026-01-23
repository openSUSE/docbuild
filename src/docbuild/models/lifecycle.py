"""Lifecycle model for docbuild."""

from enum import Flag, auto
import re
from typing import ClassVar, Self


class LifecycleFlag(Flag):
    """LifecycleFlag represents the lifecycle of a product."""

    # Order is important here
    unknown = 0
    # UNKNOWN = 0
    """Unknown lifecycle state."""

    supported = auto()
    """Supported lifecycle state."""

    beta = auto()
    """Beta lifecycle state."""

    hidden = auto()
    """Hidden lifecycle state."""

    unsupported = auto()
    """Unsupported lifecycle state."""

    # NOTE: Putting a compiled regex (or other helper) as a class
    # variable on an Enum/Flag is error-prone:
    # the Enum metaclass treats class attributes specially and may
    # convert them into members or otherwise interfere.
    #
    # Solution: This class variable will be attached after class creation.
    # _SEPARATOR = re.compile(r'[|,]')  # Static class variable

    @classmethod
    def from_str(cls: "LifecycleFlag", value: str) -> "LifecycleFlag":
        """Convert a string to a LifecycleFlag object.

        The string accepts the values 'supported', 'beta', 'hidden',
        'unsupported', or a combination of them separated by a comma or pipe.
        Additionally, the class knows the values "unknown".
        An empty string, "", is equivalent to "unknown".

        Examples:
        >>> LifecycleFlag.from_str("supported")
        <LifecycleFlag.supported: 2>
        >>> LifecycleFlag.from_str("supported,beta")
        <LifecycleFlag.supported|beta: 6>
        >>> LifecycleFlag.from_str("beta,supported|beta")
        <LifecycleFlag.supported|beta: 6>
        >>> LifecycleFlag.from_str("")
        <LifecycleFlag.unknown: 0>

        """
        separator = cls._SEPARATOR  # will exist after we attach it
        try:
            flag = cls(0)  # Start with an empty flag
            parts = [v.strip() for v in separator.split(value) if v.strip()]
            if not parts:
                return cls(0)

            for part_name in parts:
                flag |= cls.__members__[part_name]

            return flag

        except KeyError as err:
            allowed = ", ".join(cls.__members__.keys())
            raise ValueError(
                f"Invalid lifecycle name: {err.args[0]!r}. Allowed values: {allowed}",
            ) from err

    def __contains__(self: Self, other: str | Flag) -> bool:
        """Return True if self has at least one of same flags set as other.

        >>> "supported" in LifecycleFlag.beta
        False
        >>> "supported|beta" in LifecycleFlag.beta
        True
        """
        if isinstance(other, str):
            item_flag = self.__class__.from_str(other)

        elif isinstance(other, self.__class__):
            item_flag = other

        else:
            return False

        return (self & item_flag) == item_flag


# attach after class creation so EnumMeta doesn't touch it
LifecycleFlag._SEPARATOR: ClassVar[re.Pattern] = re.compile(r"[|,]")
