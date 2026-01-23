"""Products for the docbuild application."""

from enum import EnumMeta, StrEnum
from typing import Never

# from pydantic import BaseModel, computed_field
from ..constants import ALLOWED_PRODUCTS


class StrEnumMeta(EnumMeta):
    """Custom metaclass for StrEnum to allow attribute-style access."""

    def __getitem__(cls, key: str) -> "StrEnumMeta":
        """Access enum members using attribute-style names with underscores."""
        candidate = key.replace("-", "_")
        try:
            return super().__getitem__(candidate)
        except KeyError:
            allowed = ", ".join(repr(member.value) for member in cls)
            raise KeyError(
                f"{key!r} is not a valid member name or value for {cls.__name__}. "
                f"Allowed (values): {allowed}",
            ) from None


class BaseProductEnum(StrEnum, metaclass=StrEnumMeta):
    """Base class for product enums with custom error handling."""

    @classmethod
    def _missing_(cls, value: object) -> Never:
        """Raise custom error for unknown values."""
        allowed = ", ".join(repr(v.value) for v in cls)
        raise ValueError(
            f"{value!r} is not a valid {cls.__name__}. Allowed values are: {allowed}",
        )


# Products allows all our SUSE product names, but also "*" (=ALL).
# We only define "ALL" as uppercase to denote a constant, the rest is lowercase.
# Product name with dashes are replace with underscores.
# You can access "Product.sle_ha", but not "Product.sle-ha"
Product = BaseProductEnum(
    "Product",
    {"ALL": "*"} | {item.replace("-", "_"): item for item in ALLOWED_PRODUCTS},
)
"""A :py:class:`~enum.StrEnum` for the products of the docbuild application."""
