"""Pydantic models for the metadata manifest structure."""

from collections.abc import Generator
from datetime import date
from typing import ClassVar, Self

from lxml import etree
from pydantic import (
    BaseModel,
    ConfigDict,
    # model_validator,
    Field,
    SerializationInfo,
    field_serializer,
    field_validator,
)

from ..models.language import LanguageCode
from ..models.lifecycle import LifecycleFlag


class Description(BaseModel):
    """Represents a description for a product/docset.

    .. code-block:: json

        {
            "lang": "en-us",
            "default": true,
            "description": "<p>The English description for a product.</p>"
        }
    """

    lang: LanguageCode
    default: bool
    description: str

    @field_serializer("lang")
    def serialize_lang(self: Self, value: LanguageCode, info: SerializationInfo) -> str:
        """Serialize LanguageCode to a string like 'en-us'."""
        return str(value)

    @classmethod
    def from_xml_node(
        cls: type[Self], node: etree._Element
    ) -> Generator[Self, None, None]:
        """Extract descriptions from a parent XML node.

        :param node: a node pointing to ``<product>``
        :yield:
        """
        for n in node.xpath("desc"):
            text = "".join(
                f"<{child.tag}>{
                    ' '.join(
                        x.strip()
                        for t in child.itertext()
                        for x in t.splitlines()
                        if x.strip()
                    )
                }</{child.tag}>"
                for child in n.iterchildren()
                if child.tag != "title"
            )

            yield cls(**{"default": False, **n.attrib}, description=text)


class CategoryTranslation(BaseModel):
    """Represents a translation for a category title.

    .. code-block:: json

        {
            "lang": "en-us",
            "default": true,
            "title": "About"
        }
    """

    lang: LanguageCode
    default: bool = Field(default=False)
    title: str

    @field_serializer("lang")
    def serialize_lang(self: Self, value: LanguageCode, info: SerializationInfo) -> str:
        """Serialize LanguageCode to a string like 'en-us'."""
        return str(value)


class Category(BaseModel):
    """Represents a category for a product/docset.

    .. code-block:: json

        {
            "categoryId": "about",
            "rank": 1,
            "translations": [
                {
                    "lang": "en-us",
                    "default": true,
                    "title": "About"
                }
            ]
        }
    """

    _current_rank: ClassVar[int] = 0

    @staticmethod
    def _increment_rank() -> int:
        """Increments the counter and returns the next value."""
        Category._current_rank += 1
        return Category._current_rank

    id: str = Field(serialization_alias="categoryId")
    # Automatically called. Depends on the order of the XML element.
    rank: int = Field(default_factory=_increment_rank)
    translations: list[CategoryTranslation] = Field(default_factory=list)

    @classmethod
    def reset_rank(cls: type[Self]) -> None:
        """Reset the rank counter."""
        cls._current_rank = 0

    @classmethod
    def from_xml_node(
        cls: type[Self], node: etree._Element
    ) -> Generator[Self, None, None]:
        """Extract categories from a parent XML node.

        :param node: a node pointing to ``<product>``
        :yield: A :class:`Category` instance for each category found.
        """
        for cat in node.xpath("category|categories/category"):
            langs = cat.xpath("language")
            translations = [
                CategoryTranslation(
                    lang=lng.attrib.get("lang", "en-us"),
                    default=lng.attrib.get("default", False),
                    title=lng.attrib.get("title", ""),
                )
                for lng in langs
            ]
            yield cls(id=cat.attrib.get("categoryid", ""), translations=translations)


class Archive(BaseModel):
    """Represents an archive (e.g., a ZIP file) for a product/docset.

    .. code-block:: json

        {
            "lang": "en-us",
            "default": true,
            "zip": "/en-us/sles/16.0/sles-16.0-en-us.zip"
        }
    """

    lang: LanguageCode
    default: bool
    zip: str

    @field_serializer("lang")
    def serialize_lang(self: Self, value: LanguageCode, info: SerializationInfo) -> str:
        """Serialize LanguageCode to a string like 'en-us'."""
        return str(value)


class DocumentFormat(BaseModel):
    """Represents the available formats for a document.

    .. code-block:: json

        {
            "html": "/sles/16.0/html/SLE-comparison/",
            "pdf": "/sles/16.0/pdf/SLE-comparison_en.pdf"
        }
    """

    html: str
    pdf: str | None = Field(default=None, exclude_if=lambda v: v is None or v == "")
    single_html: str | None = Field(
        default=None, alias="single-html", exclude_if=lambda v: v is None or v == ""
    )


class SingleDocument(BaseModel):
    """Represent a single document.

    .. code-block:: json

        {
            "lang": "en",
            "default": true,
            "title": "Key Differences Between SLE 15 and SLE 16",
            "subtitle": "Adopting SLE 16",
            "description": "Key differences between SLE 15 and SLE 16",
            "dcfile": "DC-SLE-comparison",
            "rootid": "comparison-sle16-sle15",
            "format": {
                "html": "/sles/16.0/html/SLE-comparison/",
                "pdf": "/sles/16.0/pdf/SLE-comparison_en.pdf"
            },
            "dateModified": "2026-04-01"
        }
    """

    lang: str | None = None
    title: str
    subtitle: str = Field(default="")
    description: str
    dcfile: str
    rootid: str = Field(default="")
    format: DocumentFormat
    datemodified: date | None = Field(default=None, serialization_alias="dateModified")

    @field_serializer("datemodified")
    def serialize_date(self: Self, value: date | None, info: SerializationInfo) -> str:
        """Serialize date to 'YYYY-MM-DD' or an empty string if None."""
        if value is None:
            return ""  # This ensures the key exists as "" in JSON
        # If it's already a string (from DAPS output), return it, otherwise isoformat
        return value.isoformat() if hasattr(value, "isoformat") else str(value)


class Product(BaseModel):
    """Represents a single SUSE product.

    .. code-block:: json

        {
            "name": "SUSE Linux Enterprise Server",
            "versions": ["16.0"]
        }
    """

    name: str
    versions: list[str] = Field(default_factory=list)


class Document(BaseModel):
    """Represents a single document within the manifest.

    .. code-block:: json

        {
            "docs": [
                {
                    "lang": "en",
                    "default": true,
                    "title": "Key Differences Between SLE 15 and SLE 16",
                    "subtitle": "Adopting SLE 16",
                    "description": "Key differences between SLE 15 and SLE 16",
                    "dcfile": "DC-SLE-comparison",
                    "rootid": "comparison-sle16-sle15",
                    "format": {
                        "html": "/sles/16.0/html/SLE-comparison/",
                        "pdf": "/sles/16.0/pdf/SLE-comparison_en.pdf"
                    },
                    "dateModified": "2026-04-01"
                }
            ],
            "tasks": ["About"],
            "products": [{"name": "SUSE Linux", "versions": ["16.0"]}],
            "docTypes": [],
            "isGated": false,
            "rank": ""
        }
    """

    docs: list[SingleDocument] = Field(default_factory=list)
    tasks: list[str] = Field(default_factory=list)
    products: list[Product] = Field(default_factory=list)
    doctypes: list[str] = Field(default_factory=list, alias="docTypes")
    isgated: bool = Field(default=False, alias="isGated", serialization_alias="isGate")
    rank: int | str | None = Field(default=None)

    @field_validator("rank", mode="before")
    @classmethod
    def coerce_rank(cls: type[Self], value: str | int | None) -> int | None:
        """Coerce rank to an integer, treating empty strings or None as None to match legacy parity."""
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        return int(value)

    @field_serializer("rank")
    def serialize_rank(self: Self, value: int | str | None, info: SerializationInfo) -> str:
        """Serialize rank to an empty string if None to match legacy parity."""
        if value is None:
            return ""
        return str(value)


class Manifest(BaseModel):
    """Represents the aggregated metadata manifest for a product/docset."""

    productname: str
    acronym: str
    version: str
    lifecycle: str | LifecycleFlag = Field(default=LifecycleFlag.unknown)
    # Ensure this is defined exactly like this:
    hide_productname: bool = Field(default=False, alias="hide-productname")
    descriptions: list[Description] = Field(default_factory=list)
    categories: list[Category] = Field(default_factory=list)
    documents: list[Document] = Field(default_factory=list)
    archives: list[Archive] = Field(default_factory=list)

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True
    )

if __name__ == "__main__":  # pragma: nocover
    from rich import print  # noqa: A004

    # 1. Create a Python dictionary with example data
    example_data = {
        "productname": "SUSE Linux Enterprise Server",
        "acronym": "sles",
        "version": "15-SP6",
        "lifecycle": "supported",
        "hide_productname": False,
        "descriptions": [
            {
                "lang": "en-us",
                "default": True,
                "description": "The English description for SLES 15-SP6.",
            },
            {
                "lang": "de-de",
                "default": False,
                "description": "Die deutsche Beschreibung für SLES 15-SP6.",
            },
        ],
        "categories": [
            {
                "categoryId": "getting-started",
                "rank": 1,
                "translations": [
                    {"lang": "en-us", "default": True, "title": "Getting Started"}
                ],
            }
        ],
        "documents": [
            {
                "docs": [
                    {
                        "lang": "en",
                        "default": True,
                        "title": "Key Differences Between SUSE Linux Enterprise 15 and SUSE Linux 16",
                        "subtitle": "Adopting SUSE Linux 16",
                        "description": "Key differences between SLE 15 and SUSE Linux 16",
                        "dcfile": "DC-SLE-comparison",
                        "rootid": "comparison-sle16-sle15",
                        "format": {
                            "html": "/sles/16.0/html/SLE-comparison/",
                            "pdf": "/sles/16.0/pdf/SLE-comparison_en.pdf",
                        },
                        "dateModified": date.today().isoformat(),
                    }
                ],
                "tasks": ["About"],
                # "products": [{"name": "SUSE Linux", "versions": ["16.0"]}],
                "docTypes": [],
                "isGated": False,
                "rank": "",
            }
        ],
        "archives": [
            {"lang": "en-us", "default": True, "zip": "sles-15-SP6-en-us.zip"}
        ],
    }

    # 2. Create a Manifest instance from the dictionary
    manifest_instance = Manifest(**example_data)

    # 3. Print the resulting object using rich for a nice visual representation
    print(manifest_instance)
    print("=" * 20)
    print(manifest_instance.model_dump_json(indent=2))
