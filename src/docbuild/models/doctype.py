"""Module for defining the Doctype model."""

from collections.abc import Iterator
from itertools import product
import re
from re import Pattern
from typing import ClassVar, Self, cast

from lxml import etree  # type: ignore
from pydantic import BaseModel, Field, field_validator

from .language import LanguageCode
from .lifecycle import LifecycleFlag
from .product import Product


# --- Models
class Doctype(BaseModel):
    """A "doctype" that comprises of a product, docset, lifecycle, and language.

    The format has the following syntax:

    .. code-block:: text

       [/]?PRODUCT/DOCSETS[@LIFECYCLES]/[LANGS]

    The placeholders mean the following:

    * ``PRODUCT``: a lowercase acronym of a SUSE product, e.g. ``sles``
    * ``DOCSETS``: one or more docsets of the mentioned product, separated by comma
    * ``LIFECYCLES``: zero or more lifecycles, separated by comma or pipe.
      Default to ``unknown`` if omitted.
    * ``LANGS``: zero or more languages, separated by comma.
      Default to English (``en-us``) if omitted.

    :raises pydantic_core.ValidationError: if the input values are invalid.

    >>> doctype = Doctype.from_str("sles/15-SP6@supported/en-us,de-de")
    >>> doctype.product
    <Product.sles: 'sles'>
    <Product.sles: 'SUSE Linux Enterprise Server'>
    >>> doctype.docset
    ['15-SP6']
    >>> doctype.lifecycle.name
    'supported'
    >>> doctype.langs
    [LanguageCode(language='de-de'), LanguageCode(language='en-us')]
    """

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
        default=LifecycleFlag.unknown,
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
        default=[LanguageCode(language="en-us")],
        description=(
            "The natural language containing language and country. "
            "Values can be combined using commas. "
            "After validation, langs are sorted"
        ),
        examples=["en-us", "de-de"],
    )
    """A natural language containing language and country"""

    # Pre-compile regex for efficiency
    # The regex contains non-capturing groups on purpose
    # This leads to None in the result if that group isn't matched
    _DOCTYPE_REGEX: ClassVar[Pattern] = re.compile(
        r"^"                                 # start
        r"(?:/?([^/@]+|\*))?"                # optional product (group 1)
        r"/(?:([^/@]+|\*))?"                 # optional docset (group 2)
        r"(?:@([a-z]+(?:[,|][a-z]+)*))?"     # optional lifecycle (group 3)
        r"(?:/(\*|[\w-]+(?:,[\w-]+)*)?)?$",  # optional langs (group 4)
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
        return f"{self.product.acronym}/{docset_str}@{self.lifecycle.name}/{langs_str}"

    def __repr__(self: Self) -> str:
        """Implement repr(self)."""
        langs_str = ",".join(lang.language for lang in self.langs)
        docset_str = ",".join(self.docset)
        return (
            f"{self.__class__.__name__}(product={self.product.acronym!r}, "
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
                self.product == other.product or self.product is Product.ALL,
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

    def iter_doctypes(self: Self,
                      portal_root: etree._Element | None = None) -> Iterator["Doctype"]:
        """Iterate over all docset and language combinations.

        The iteration order is docset-major: for each docset, iterate all
        languages. This is the Cartesian product of ``docset`` and ``langs``.

        If ``portal_root`` is given, wildcard values (``*``) are expanded from
        the parsed portal XML tree. Without ``portal_root``, wildcards remain
        symbolic.

        >>> doctype = Doctype.from_str("sles/15-SP6,15-SP7/en-us,de-de")
        >>> [
        ...     f"{item.product.value}/{item.docset[0]}/{item.langs[0].language}"
        ...     for item in doctype.iter_doctypes()
        ... ]
        ['sles/15-SP6/de-de', 'sles/15-SP6/en-us', 'sles/15-SP7/de-de', 'sles/15-SP7/en-us']
        """
        has_product_wildcard = self.product is Product.ALL
        has_docset_wildcard = "*" in self.docset
        has_lang_wildcard = any(lang.language == "*" for lang in self.langs)

        product_values = [self.product]
        if portal_root is not None and has_product_wildcard:
            product_values = [
                self.coerce_product(product_id)
                for product_id in sorted(
                    {
                        product_id
                        for product_id in portal_root.xpath("product/@id")
                        if product_id
                    },
                )
            ]

        combinations: set[tuple[Product, str, LanguageCode]] = set()

        for product_value in product_values:
            docsets = self.docset
            if portal_root is not None and has_docset_wildcard:
                docsets = sorted(
                    {
                        cast(str, docset)
                        for docset in portal_root.xpath(
                            f"product[@id={product_value.acronym!r}]/docset/@path",
                        )
                        if docset
                    },
                )

            docset_lang_pairs = {
                (docset, lang) for docset, lang in product(docsets, self.langs)
            }
            if portal_root is not None and has_lang_wildcard:
                docset_lang_pairs: set[tuple[str, LanguageCode]] = {
                    (docset, LanguageCode(language=lang))
                    for docset in docsets
                    for lang in sorted(
                        {
                            cast(str, lang)
                            for lang in portal_root.xpath(
                                (
                                    f"product[@id={product_value.acronym!r}]"
                                    f"/docset[@path={docset!r}]"
                                    "/resources/locale/@lang"
                                ),
                            )
                            if lang
                        },
                    )
                }

            combinations.update(
                (product_value, docset, lang)
                for docset, lang in docset_lang_pairs
            )

        for product_value, docset, lang in sorted(
            combinations,
            key=lambda item: (item[0].acronym, item[1], item[2].language),
        ):
            yield self.model_copy(
                update={
                    "product": product_value,
                    "docset": [docset],
                    "langs": [lang],
                },
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
    def from_str(cls: type["Doctype"],
                 doctype_str: str,
                 *,
                 default_lang: str="en-us") -> "Doctype":
        """Parse a string that adheres to the doctype format.

        :param doctype_str: A string that adheres to the doctype format.
        :param default_lang: The default language to use if none is specified (by default, "en-us").
        :return: A Doctype object.
        :raise ValueError: If the input string is invalid.

        The language segment is optional: ``sles/16`` and ``sles/16/`` all select
        English (``en-us``) by default, while ``sles/16/*`` and ``sles/16@supported/*``
        are all equivalent and select *all* languages.
        """
        match = cls._DOCTYPE_REGEX.match(doctype_str)

        if not match:
            raise ValueError(f"Invalid doctype string format: {doctype_str!r}")

        product, docset, lifecycle, langs = match.groups()
        product = "*" if not product else product
        docset = "*" if not docset else docset
        lifecycle = "unknown" if lifecycle is None else lifecycle
        langs = default_lang if langs is None else langs
        return cls(
            product=cls.coerce_product(product),
            docset=docset,
            lifecycle=lifecycle,
            langs=langs,
        )

    def xpath(self: Self, absolute:bool=False) -> str:
        """Return an XPath expression for this Doctype to find all deliverables.

        >>> result = Doctype.from_str("sles/15-SP6@supported/en-us,de-de").xpath(absolute=True)
        >>> expected = (
        ...     "//product[@id='sles']/docset[@path='15-SP6']"
        ...     "[@lifecycle='supported']"
        ...     "/resources/locale[@lang='de-de' or @lang='en-us']"
        ...     "/deliverable"
        ... )
        >>> result == expected
        True

        :return: An XPath expression that can be used to find all
            deliverables that match this Doctype.
        """
        # Example: /sles/15-SP6@supported/en-us,de-de
        product = "product"
        if self.product is not Product.ALL:
            product += f"[@id={self.product.acronym!r}]"

        docset = self.docset_xpath_segment()
        docset += self.lifecycle_xpath_segment()
        locale = self.locale_xpath_segment()
        return f"{product}/{docset}/resources/{locale}"

    def product_xpath_segment(self: Self) -> str:
        """Return the XPath segment for the product node.

        Example: "product[@id='sles']" or "product"
        """
        if self.product is not Product.ALL:
            return f"product[@id={self.product.acronym!r}]"
        return "product"

    def docset_xpath_segment(self: Self, docset: str | None = None) -> str:
        """Return the XPath segment for the docset node.

        Example: "docset[@path='15-SP6']" or "docset"
        """
        if docset is not None:
            if docset != "*":
                return f"docset[@path={docset!r}]"
            return "docset"

        if self.docset and "*" not in self.docset:
            setids = [f"@path={d!r}" for d in self.docset if d != "*"]
            setids_str = " or ".join(setids)
            return f"docset[{setids_str}]"
        return "docset"

    def lifecycle_xpath_segment(self: Self) -> str:
        """Return the XPath segment for the lifecycle node.

        Example: "docset[@lifecycle='supported']" or "docset"
        """
        if self.lifecycle and self.lifecycle != LifecycleFlag.unknown:
            lifecycle = " or ".join(
                [
                    f"@lifecycle={lc.name!r}"
                    for lc in self.lifecycle
                ]
            )
            return f"[{lifecycle}]"
        return ""

    def locale_xpath_segment(self: Self) -> str:
        """Return the XPath segment for the language node.

        Example: "resources/locale[@lang='en-us']" or "resources/locale"
        """
        language = "locale"
        has_wildcard = any(lang.language == "*" for lang in self.langs)
        if self.langs and not has_wildcard:
            language = " or ".join([f"@lang={lang.language!r}" for lang in self.langs])
            language = f"locale[{language}]"
        elif not self.langs:
            # Toms' Suggestion: Fallback to English if no language is specified
            language += "[@lang='en-us']"
        return language
