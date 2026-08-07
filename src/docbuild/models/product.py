"""Products for the docbuild application."""

from enum import EnumMeta, StrEnum
from typing import Self, cast


class StrEnumMeta(EnumMeta):
    """Custom metaclass for StrEnum to allow attribute-style access."""

    def __getitem__(cls, name: str) -> object:
        """Access enum members using attribute-style names with underscores."""
        candidate = name.replace("-", "_")
        try:
            return super().__getitem__(candidate)
        except KeyError:
            allowed = ", ".join(
                repr(cast(StrEnum, member).value) for member in cls
            )
            raise KeyError(
                f"{name!r} is not a valid member name or value for {cls.__name__}. "
                f"Allowed (values): {allowed}",
            ) from None


class BaseProductEnum(StrEnum, metaclass=StrEnumMeta):
    """Base class for product enums with custom error handling."""

    @classmethod
    def _missing_(cls, value: object) -> Self | None:
        """Raise custom error for unknown values."""
        allowed = ", ".join(repr(v.value) for v in cls)
        raise ValueError(
            f"{value!r} is not a valid {cls.__name__}. Allowed values are: {allowed}",
        )


class Product(BaseProductEnum):
    """A :class:`~enum.StrEnum` for all known products, including wildcard ``*``.

    The enum value stores the full product name, while :attr:`acronym` exposes
    the canonical short ID used in doctypes and XML product IDs.
    """

    # Acronoym = Name
    ALL = "*"
    appliance = "Appliance building"
    cloudnative = "Cloud Native"
    compliance = "Compliance Documentation"
    container = "Container Documentation"
    liberty = "SUSE Multi-Linux Support"
    releasenotes = "SUSE Release Notes"
    sbp = "SUSE Best Practices"
    ses = "SUSE Enterprise Storage"
    sled = "SUSE Linux Enterprise Desktop"
    sle_ha = "SUSE Linux Enterprise High Availability"
    sle_hpc = "SUSE Linux Enterprise High-Performance Computing"
    sle_micro = "SUSE Linux Micro"
    sle_public_cloud = "SUSE Linux Enterprise in Public Clouds"
    sle_rt = "SUSE Linux Enterprise Real Time"
    sles_sap = "SUSE Linux Enterprise Server for SAP applications"
    sles = "SUSE Linux Enterprise Server"
    sle_vmdp = "SUSE Linux Enterprise Virtual Machine Driver Pack"
    smart = "SUSE Smart Docs"
    smt = "SUSE Linux Enterprise Subscription Management Tool"
    soc = "SUSE OpenStack Cloud"
    style = "SUSE Documentation Style Guide"
    subscription = "Subscription Management"
    suma_retail = "SUSE Multi-Linux Manager for Retail"
    suma = "SUSE Multi-Linux Manager"
    suse_ai_factory = "SUSE AI Factory"
    suse_ai = "SUSE AI"
    suse_caasp = "SUSE CaaS Platform"
    suse_cap = "SUSE Cloud Application Platform"
    suse_distribution_migration_system = "SUSE Distribution Migration System"
    suse_edge = "SUSE Edge"
    suse_telco = "SUSE Telco Cloud"
    trd = "Technical Reference Documentation"

    @property
    def acronym(self) -> str:
        """Return the canonical product acronym used in doctypes and XML IDs."""
        if self is Product.ALL:
            return "*"
        return self.name.replace("_", "-")

    @classmethod
    def _missing_(cls, value: object) -> Self | None:
        """Accept acronym input in addition to the full product name.

        This intentionally overrides :meth:`BaseProductEnum._missing_`, which
        only raises a formatted :class:`ValueError`. Here we add product-specific
        coercion rules (acronyms and ``*``), then fall back to the base method.
        """
        if isinstance(value, str):
            if value == "*":
                return cast(Self, cls.ALL)

            candidate = value.strip().replace("-", "_")
            if member := cls.__members__.get(candidate):
                return cast(Self, member)

        return super()._missing_(value)
