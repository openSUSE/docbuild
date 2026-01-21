"""Module for defining the Doctype model."""

import re
from re import Pattern
from typing import ClassVar, Self

from pydantic import BaseModel, Field, field_validator

from .language import LanguageCode
from .lifecycle import LifecycleFlag
from .product import Product


# --- Models
class Doctype(BaseModel):
    """A "doctype" that comprises of a product, docset, lifecycle, and language.

    The format has the following syntax:

    .. code-block:: text

       [/]?[PRODUCT]/[DOCSETS][@LIFECYCLES]/LANGS

    The placeholders mean the following:

    * ``PRODUCT``: a lowercase acronym of a SUSE product, e.g. ``sles``
    * ``DOCSETS``: one or more docsets of the mentioned product, separated by comma
    * ``LIFECYCLES``: one or more lifecycles, separated by comma or pipe
    * ``LANGS``: one or more languages, separated by comma

    >>> doctype = Doctype.from_str("sles/15-SP6@supported/en-us,de-de")
    >>> doctype.product
    <Product.sles: 'sles'>
    >>> doctype.docset
    ['15-SP6']
    >>> doctype.lifecycle.name
    'supported'
    >>> doctype.langs
    [LanguageCode(language='de-de'), LanguageCode(language='en-us')]
    """

    # __init__.__doc__ = """Create a new Doctype instance.

    # :param product: A SUSE product, e.g. 'sles', 'smart'.
    # :param docset: A specific release or version of a product.
    # :param lifecycle: The state of the Doctype, e.g. 'supported', 'beta'.
    # :param langs: A natural language, e.g. 'en-us', 'de-de'.

    # :raises pydantic_core.ValidationError: if the input values are invalid.
    # """   # type: ignore

    product: Product = Field(
        title="A SUSE product",
        description="A SUSE product is a lowercase acronym.",
        examples=["sles", "smart"],
    )
    """A SUSE product is a lowercase acronym"""

    docset: list[str] = Field(
        title="A specific 'docset' of a product",
        description=(
            "A specific release or version of a product. "
            "Values can be combined using commas. "
            "After validation, docsets are sorted."
        ),
        examples=["15-SP6", "systems-management"],
    )
    """A specific 'docset' of a product (usually a release or version)"""

    lifecycle: LifecycleFlag = Field(
        title="The state of the Doctype",
        description=(
            "One or more lifecycle states that indicate the "
            "support or development. "
            "Values can be combined using commas or pipes."
        ),
        examples=["supported", "beta", "unsupported"],
    )
    """The state  (supported, beta, etc.) of the Doctype"""

    langs: list[LanguageCode] = Field(
        title="A natural language",
        description=(
            "The natural language containing language and country. "
            "After validation, langs are sorted"
        ),
        examples=["en-us", "de-de"],
    )
    """A natural language containing language and country"""

    # Pre-compile regex for efficiency
    # The regex contains non-capturing groups on purpose
    # This leads to None in the result if that group isn't matched
    _DOCTYPE_REGEX: ClassVar[Pattern] = re.compile(
        r"^"  # start
        r"(?:/?([^/@]+|\*))?"  # optional product (group 1)
        r"/(?:([^/@]+|\*))?"  # optional docset (group 2)
        r"(?:@([a-z]+(?:[,|][a-z]+)*))?"  # optional lifecycle (group 3)
        r"/(\*|[\w-]+(?:,[\w-]+)*)$",  # required langs (group 4)
    )

    # dunder methods
    def __eq__(self: Self, other: object) -> bool:
        """Check equality with another Doctype, ignoring order in docset/langs."""
        if not isinstance(other, Doctype):
            return NotImplemented

        return (
            self.product == other.product
            and self.lifecycle == other.lifecycle
            and set(self.docset) == set(other.docset)
            and set(self.langs) == set(other.langs)
        )

    def __lt__(self: Self, other: object) -> bool:
        """Check if this Doctype is less than another Doctype."""
        if not isinstance(other, Doctype):
            return NotImplemented

        # Define sort priority: product > lifecycle > docset > langs
        return (
            self.product,
            self.lifecycle,
            self.docset,  # we rely on a sorted docset
            self.langs,  # we rely on sorted languages
        ) < (other.product, other.lifecycle, other.docset, other.langs)

    def __str__(self: Self) -> str:
        """Implement str(self)."""
        langs_str = ",".join(lang.language for lang in self.langs)
        docset_str = ",".join(self.docset)
        return f"{self.product.value}/{docset_str}@{self.lifecycle.name}/{langs_str}"

    def __repr__(self: Self) -> str:
        """Implement repr(self)."""
        langs_str = ",".join(lang.language for lang in self.langs)
        docset_str = ",".join(self.docset)
        return (
            f"{self.__class__.__name__}(product={self.product.value!r}, "
            f"docset=[{docset_str}], "
            f"lifecycle={self.lifecycle.name!r}, "
            f"langs=[{langs_str}]"
            f")"
        )

    def __contains__(self: Self, other: "Doctype") -> bool:
        """Return if bool(other in self).

        Every part of a Doctype is compared element-wise.
        """
        if not isinstance(other, Doctype):
            return NotImplemented

        return all(
            [
                self.product == other.product or self.product == Product.ALL,
                set(other.docset).issubset(self.docset) or "*" in self.docset,
                other.lifecycle in self.lifecycle,
                set(other.langs).issubset(self.langs) or "*" in self.langs,
            ],
        )

    def __hash__(self: Self) -> int:
        """Implement hash(self)."""
        return hash(
            (
                self.product,
                tuple(self.docset),
                tuple(self.langs),
            ),
        )

    # Validators
    @field_validator("product", mode="before")
    @classmethod
    def coerce_product(cls, value: str | Product) -> Product:
        """Convert a string into a valid Product."""
        return value if isinstance(value, Product) else Product(value)

    @field_validator("docset", mode="before")
    @classmethod
    def coerce_docset(cls, value: str | list[str]) -> list[str]:
        """Convert a string into a list."""
        return sorted(value.split(",")) if isinstance(value, str) else sorted(value)

    @field_validator("langs", mode="before")
    @classmethod
    def coerce_langs(cls: type["Doctype"], value: str | list[str | LanguageCode]) -> list[LanguageCode]:
        """Convert a comma-separated string or a list of strings into LanguageCode."""
        # Allow list of strings or Language enums
        if isinstance(value, str):
            value = sorted(value.split(","))
        return sorted(
            [
                lang if isinstance(lang, LanguageCode) else LanguageCode(language=lang)
                for lang in value
            ]
        )

    @classmethod
    def from_str(cls: type["Doctype"], doctype_str: str) -> Self:
        """Parse a string that adheres to the doctype format."""
        match = cls._DOCTYPE_REGEX.match(doctype_str)

        if not match:
            raise ValueError(f"Invalid doctype string format: {doctype_str!r}")

        product, docset, lifecycle, langs = match.groups()
        product = "*" if not product else product
        docset = "*" if not docset else docset
        lifecycle = "unknown" if lifecycle is None else lifecycle
        langs = "en-us" if langs is None else langs
        return cls(
            product=product,
            docset=docset,
            lifecycle=lifecycle,
            langs=langs,
        )

    def xpath(self: Self) -> str:
        """Return an XPath expression for this Doctype to find all deliverables.

        >>> result = Doctype.from_str("sles/15-SP6@supported/en-us,de-de").xpath()
        >>> expected = (
        ...     "product[@productid='sles']/docset[@setid='15-SP6']"
        ...     "[@lifecycle='supported']"
        ...     "/builddocs/language[@lang='de-de' or @lang='en-us']"
        ... )
        >>> result == expected
        True

        :return: A relative XPath expression that can be used to find all
            deliverables that match this Doctype.
        """
        # Example: /sles/15-SP6@supported/en-us,de-de
        product = "product"
        if self.product != Product.ALL:
            product += f"[@productid={self.product.value!r}]"

        setids = [f"@setid={d!r}" for d in self.docset if d != "*"]

        setids_str = " or ".join(setids)
        if setids_str:
            docset = f"docset[{setids_str}]"
        else:
            docset = "docset"

        lifecycle = " or ".join(
            [
                f"@lifecycle={lc.name!r}"
                for lc in self.lifecycle
                if lc != LifecycleFlag.unknown
            ]
        )
        if lifecycle:
            docset += f"[{lifecycle}]"

        if "*" in self.langs:
            language = "language"
        else:
            language = " or ".join([f"@lang={lang.language!r}" for lang in self.langs])
            language = f"language[{language}]"

        return f"{product}/{docset}/builddocs/{language}"

    def product_xpath_segment(self: Self) -> str:
        """Return the XPath segment for the product node.

        Example: "product[@productid='sles']" or "product"
        """
        if self.product != Product.ALL:
            return f"product[@productid={self.product.value!r}]"
        return "product"

    def docset_xpath_segment(self: Self, docset: str) -> str:
        """Return the XPath segment for the docset node.

        Example: "docset[@setid='15-SP6']" or "docset"
        """
        if docset != "*":
            return f"docset[@setid={docset!r}]"
        return "docset"
