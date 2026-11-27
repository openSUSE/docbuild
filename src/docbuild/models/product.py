"""Product definitions and read-only catalog for the docbuild application."""

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from difflib import get_close_matches
from enum import EnumMeta, StrEnum
from types import MappingProxyType
from typing import Self, cast

# Default acronym -> full display name mapping used when no custom catalog is supplied.
DEFAULT_PRODUCT_NAMES: dict[str, str] = {
    "*": "*",
    "appliance": "Appliance building",
    "cloudnative": "Cloud Native",
    "compliance": "Compliance Documentation",
    "container": "Container Documentation",
    "liberty": "SUSE Multi-Linux Support",
    "releasenotes": "SUSE Release Notes",
    "sbp": "SUSE Best Practices",
    "ses": "SUSE Enterprise Storage",
    "sled": "SUSE Linux Enterprise Desktop",
    "sle-ha": "SUSE Linux Enterprise High Availability",
    "sle-hpc": "SUSE Linux Enterprise High-Performance Computing",
    "sle-micro": "SUSE Linux Micro",
    "sle-public-cloud": "SUSE Linux Enterprise in Public Clouds",
    "sle-rt": "SUSE Linux Enterprise Real Time",
    "sles-sap": "SUSE Linux Enterprise Server for SAP applications",
    "sles": "SUSE Linux Enterprise Server",
    "sles-nvidia": "SUSE Linux Enterprise Server for NVIDIA",
    "sle-vmdp": "SUSE Linux Enterprise Virtual Machine Driver Pack",
    "smart": "SUSE Smart Docs",
    "smt": "SUSE Linux Enterprise Subscription Management Tool",
    "soc": "SUSE OpenStack Cloud",
    "style": "SUSE Documentation Style Guide",
    "subscription": "Subscription Management",
    "suma-retail": "SUSE Multi-Linux Manager for Retail",
    "suma": "SUSE Multi-Linux Manager",
    "suse-ai-factory": "SUSE AI Factory",
    "suse-ai": "SUSE AI",
    "suse-caasp": "SUSE CaaS Platform",
    "suse-cap": "SUSE Cloud Application Platform",
    "suse-distribution-migration-system": "SUSE Distribution Migration System",
    "suse-edge": "SUSE Edge",
    "suse-telco": "SUSE Telco Cloud",
    "trd": "Technical Reference Documentation",
}


@dataclass(frozen=True, slots=True)
class ProductInfo:
    """Immutable representation of a single product."""

    acronym: str
    name: str

    def __str__(self) -> str:
        """Return the product's full display name."""
        return self.name


def normalize_product_acronym(acronym: str) -> str:
    """Normalize a product acronym to canonical lowercase hyphenated form."""
    normalized = acronym.strip().lower().replace("_", "-")
    if normalized == "*":
        return "*"
    return normalized


@dataclass(frozen=True, slots=True)
class ProductCatalog:
    """Read-only collection of known products keyed by canonical acronym."""

    _products: Mapping[str, ProductInfo]

    def __post_init__(self) -> None:
        """Ensure internal mapping cannot be mutated after construction."""
        if not isinstance(self._products, MappingProxyType):
            object.__setattr__(
                self,
                "_products",
                MappingProxyType(dict(self._products)),
            )

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, str]) -> "ProductCatalog":
        """Build a read-only catalog from an ``{acronym: name}`` mapping."""
        entries: dict[str, ProductInfo] = {}
        for raw_acronym, raw_name in mapping.items():
            acronym = normalize_product_acronym(raw_acronym)
            name = raw_name.strip()
            if not acronym or not name:
                raise ValueError(
                    f"Invalid product entry {raw_acronym!r}={raw_name!r}: "
                    "acronym and name must be non-empty."
                )
            entries[acronym] = ProductInfo(acronym=acronym, name=name)
        return cls(_products=MappingProxyType(entries))

    @classmethod
    def default(cls) -> "ProductCatalog":
        """Return the built-in default product catalog."""
        return cls.from_mapping(DEFAULT_PRODUCT_NAMES)

    def get(self, acronym: str) -> ProductInfo | None:
        """Look up a product by acronym, returning ``None`` if absent."""
        return self._products.get(normalize_product_acronym(acronym))

    def __getitem__(self, acronym: str) -> ProductInfo:
        """Look up a product by acronym or raise ``KeyError`` with hints."""
        key = normalize_product_acronym(acronym)
        if key in self._products:
            return self._products[key]
        allowed = ", ".join(repr(k) for k in self._products)
        raise KeyError(
            f"{acronym!r} is not a valid product acronym. Allowed: {allowed}"
        )

    def __contains__(self, acronym: object) -> bool:
        """Return whether *acronym* is present in the catalog."""
        if not isinstance(acronym, str):
            return False
        return normalize_product_acronym(acronym) in self._products

    def __iter__(self) -> Iterator[ProductInfo]:
        """Iterate over :class:`ProductInfo` entries in insertion order."""
        return iter(self._products.values())

    def __len__(self) -> int:
        """Return number of products in the catalog."""
        return len(self._products)

    @property
    def acronyms(self) -> tuple[str, ...]:
        """Return all configured product acronyms as an immutable tuple."""
        return tuple(self._products.keys())

    def suggest(self, acronym: str, limit: int = 3) -> list[str]:
        """Return close-match product acronyms for typo reporting."""
        candidates = [k for k in self._products if k != "*"]
        return get_close_matches(normalize_product_acronym(acronym), candidates, n=limit)


class StrEnumMeta(EnumMeta):
    """Custom metaclass for StrEnum to allow attribute-style access."""

    def __getitem__(cls, name: str) -> object:
        """Access enum members using attribute-style names with underscores.

        Dashes in ``name`` are replaced with underscores first, so the
        acronym can be used as well.

        :param name: The member name or acronym, for example ``sle-ha``.
        :return: The matching enum member.
        :raises KeyError: If no member has this name.

        >>> Product["sle-ha"]
        <Product.sle_ha: 'SUSE Linux Enterprise High Availability'>
        """
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
        """Raise custom error for unknown values.

        :param value: The value that did not match a member.
        :raises ValueError: Always, with a list of the allowed values.
        """
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
    sles_nvidia = "SUSE Linux Enterprise Server for NVIDIA"
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

        :param value: The value that did not match a member.
        :return: The member with this acronym, or ``Product.ALL`` for ``*``.
        :raises ValueError: If ``value`` is not a known acronym.

        >>> Product("sle-micro")
        <Product.sle_micro: 'SUSE Linux Micro'>
        """
        if isinstance(value, str):
            if value == "*":
                return cast(Self, cls.ALL)

            candidate = value.strip().replace("-", "_")
            if member := cls.__members__.get(candidate):
                return cast(Self, member)

        allowed = ", ".join(repr(member.acronym) for member in cls)
        raise ValueError(
            f"{value!r} is not a valid {cls.__name__}. Allowed values are: {allowed}",
        )
