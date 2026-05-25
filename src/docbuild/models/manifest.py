"""Pydantic models for the metadata manifest structure."""

from collections.abc import Generator
from datetime import date
import logging
import re
from typing import TYPE_CHECKING, ClassVar, Self

if TYPE_CHECKING:
    from .deliverable import Deliverable

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    SerializationInfo,
    ValidationInfo,
    field_serializer,
    field_validator,
    model_validator,
)

from ..models.language import LanguageCode
from ..models.lifecycle import LifecycleFlag

log = logging.getLogger(__name__)

_PRODUCT_PATTERN = re.compile(r"\[(.*?)\](.*)")


def _coerce_metadata_payload(payload: dict[str, object]) -> dict[str, object]:
    """Return a merged metadata payload for model validation."""
    metadata = payload.get("metadata")
    if isinstance(metadata, dict):
        merged = dict(metadata)
        for key, value in payload.items():
            if key != "metadata" and key not in merged:
                merged[key] = value
        return merged
    return payload


def _first_value(payload: dict[str, object], *keys: str) -> object | None:
    """Return the first non-null payload value for the provided keys."""
    for key in keys:
        value = payload.get(key)
        if value is not None:
            return value
    return None


def _split_text_list(value: object) -> list[str]:
    """Split a metadata value into a list of non-empty strings."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        if ";" in value:
            parts = value.split(";")
        elif "," in value:
            parts = value.split(",")
        else:
            parts = [value]
        return [part.strip() for part in parts if part.strip()]
    text = str(value).strip()
    return [text] if text else []


def _normalize_products(value: object) -> list[dict[str, object]]:
    """Normalize product entries from metadata payloads."""
    products: list[dict[str, object]] = []
    items = value if isinstance(value, list) else [value]

    for item in items:
        if isinstance(item, dict):
            name = (
                item.get("name")
                or item.get("product")
                or item.get("productname")
                or ""
            )
            versions_value = item.get("versions") or item.get("version") or []
            versions = _split_text_list(versions_value)
            products.append({"name": str(name), "versions": versions})
            continue

        if isinstance(item, str):
            if match := _PRODUCT_PATTERN.match(item):
                versions = _split_text_list(match.group(1))
                name = match.group(2).strip()
            else:
                name = item.strip()
                versions = []
            if name:
                products.append({"name": name, "versions": versions})
            continue

        name = str(item).strip()
        if name:
            products.append({"name": name, "versions": []})

    return products


def _normalize_docs(payload: dict[str, object]) -> list[dict[str, object]]:
    """Normalize document payloads into a list of doc dicts."""
    docs_value = payload.get("docs")
    if isinstance(docs_value, list) and docs_value:
        raw_docs = docs_value
    elif isinstance(docs_value, dict):
        raw_docs = [docs_value]
    else:
        doc_value = payload.get("document") or payload.get("doc")
        raw_docs = [doc_value] if isinstance(doc_value, dict) else [payload]

    description = _first_value(
        payload,
        "description",
        "seo-description",
        "seo_description",
        "seoDescription",
    )
    normalized: list[dict[str, object]] = []
    for doc in raw_docs:
        if not isinstance(doc, dict):
            continue
        doc_data = dict(doc)
        if description and not doc_data.get("description"):
            doc_data["description"] = str(description)
        if "rootId" in doc_data and "rootid" not in doc_data:
            doc_data["rootid"] = doc_data["rootId"]
        normalized.append(doc_data)

    return normalized


def _normalize_document_payload(payload: dict[str, object]) -> dict[str, object]:
    """Normalize a metadata payload into Document-compatible data."""
    payload = _coerce_metadata_payload(payload)
    normalized = dict(payload)
    normalized["docs"] = _normalize_docs(payload)

    tasks_value = _first_value(payload, "tasks", "task")
    normalized["tasks"] = _split_text_list(tasks_value)

    products_value = _first_value(payload, "products", "productname")
    normalized["products"] = _normalize_products(products_value)
    return normalized


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
    description: str = Field(default="")

    @field_serializer("lang")
    def serialize_lang(self: Self, value: LanguageCode, info: SerializationInfo) -> str:
        """Serialize LanguageCode to a string like 'en-us'."""
        return str(value)

    @classmethod
    def from_xml_node(
        cls: type[Self], deliverable: "Deliverable"
    ) -> Generator[Self, None, None]:
        """Extract descriptions from a deliverable object.

        :param deliverable: A deliverable object.
        :yield: A :class:`Description` instance for each description found.
        """
        for n in deliverable.xml.desc():
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
        cls: type[Self], deliverable: "Deliverable"
    ) -> Generator[Self, None, None]:
        """Extract categories from a deliverable object.

        :param deliverable: A deliverable object.
        :yield: A :class:`Category` instance for each category found.
        """
        for cat in deliverable.xml.categories():
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

    html: str = Field(default="")
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

    # Define dcfile first so it is available to other validators in 'info.data'
    dcfile: str = Field(default="")
    lang: str | None = None
    title: str | None = Field(default=None)
    subtitle: str = Field(default="")
    description: str = Field(default="")
    rootid: str = Field(default="")
    format: DocumentFormat = Field(default_factory=DocumentFormat)
    datemodified: date | None = Field(
        default=None,
        alias="dateModified",
        serialization_alias="dateModified",
        validation_alias=AliasChoices("dateModified", "date_modified", "date"),
    )

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    @field_validator("datemodified", mode="before")
    @classmethod
    def parse_datemodified(cls, value: object, info: ValidationInfo) -> date | None:
        """Parse dateModified values and warn on invalid values."""
        if value is None or value == "":
            return None
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            try:
                return date.fromisoformat(value)
            except ValueError:
                # origin = info.data.get("dcfile", "Unknown Origin")
                lang = info.data.get("lang", "Unknown Lang")
                rootid = info.data.get("rootid", "Unknown RootID")
                log.warning(
                    "Invalid dateModified for rootid=%s (Lang: %s): %s",
                    rootid,
                    lang,
                    value,
                )
                return None
        return None

    @field_validator("title")
    @classmethod
    def warn_missing_title(cls, v: str | None, info: ValidationInfo) -> str | None:
        """Check for missing titles and log a warning with the document origin."""
        # info.data contains fields defined before 'title'
        origin = info.data.get("dcfile", "Unknown Origin")
        lang = info.data.get("lang", "Unknown Lang")

        # Catch both None and empty strings
        if not v:
            log.warning(
                "Metadata Integrity: Document missing title. Origin: %s (Lang: %s)",
                origin, lang
            )
        return v

    @field_serializer("datemodified")
    def serialize_date(self: Self, value: date | None, _info: SerializationInfo) -> str:
        """Serialize date to 'YYYY-MM-DD' or an empty string if None."""
        if value is None:
            return ""  # TODO: Consider a fallback?
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

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    @model_validator(mode="before")
    @classmethod
    def normalize_payload(cls: type[Self], data: object) -> object:
        """Normalize raw metadata payloads into a document structure."""
        if not isinstance(data, dict):
            return data
        return _normalize_document_payload(data)

    @classmethod
    def from_metadata_payload(
        cls: type[Self],
        payload: dict[str, object],
        *,
        dcfile: str,
        lang: str,
    ) -> Self:
        """Create a Document from raw metadata payloads.

        :param payload: Raw metadata payload.
        :param dcfile: DC file name for the deliverable.
        :param lang: Deliverable language.
        :return: Normalized Document instance.
        """
        normalized = _normalize_document_payload(payload)
        docs = normalized.get("docs")
        if isinstance(docs, list) and docs:
            doc = docs[0]
            if isinstance(doc, dict):
                doc.setdefault("dcfile", dcfile)
                doc.setdefault("lang", lang)
        return cls.model_validate(normalized)

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
