"""Pydantic model for validating JSON-LD metadata embedded in HTML."""

from datetime import datetime
from typing import Annotated, Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
)

NonEmptyString = Annotated[
    str,
    StringConstraints(strict=True, strip_whitespace=True, min_length=1),
]


class JsonLDImage(BaseModel):
    """Image referenced by JSON-LD metadata."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    type: NonEmptyString | list[NonEmptyString] | None = Field(
        default=None, alias="@type", description="Schema.org image type"
    )
    url: NonEmptyString | None = Field(default=None, description="Image URL")


class JsonLDEntity(BaseModel):
    """Organization, topic, series, or software described in JSON-LD."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    type: NonEmptyString | list[NonEmptyString] | None = Field(
        default=None, alias="@type", description="Schema.org entity type"
    )
    name: NonEmptyString | None = Field(default=None, description="Entity name")
    url: NonEmptyString | None = Field(default=None, description="Entity URL")
    logo: JsonLDImage | None = Field(default=None, description="Organization logo")
    software_version: NonEmptyString | None = Field(
        default=None, alias="softwareVersion", description="Software version"
    )
    application_category: NonEmptyString | None = Field(
        default=None, alias="applicationCategory", description="Application category"
    )
    operating_system: NonEmptyString | None = Field(
        default=None, alias="operatingSystem", description="Supported operating system"
    )
    processor_requirements: NonEmptyString | None = Field(
        default=None, alias="processorRequirements", description="Supported processors"
    )


class JsonLD(BaseModel):
    """JSON-LD metadata used for an article."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    context: NonEmptyString | dict[str, Any] | list[NonEmptyString | dict[str, Any]] | None = Field(
        default=None, alias="@context", description="JSON-LD context"
    )
    type: NonEmptyString | list[NonEmptyString] | None = Field(
        default=None, alias="@type", description="Schema.org article type"
    )
    image: NonEmptyString | JsonLDImage | list[NonEmptyString | JsonLDImage] | None = Field(
        default=None, description="Article image"
    )
    name: NonEmptyString | None = Field(default=None, description="Article title")
    is_part_of: JsonLDEntity | None = Field(
        default=None, alias="isPartOf", description="Containing publication"
    )
    in_language: NonEmptyString | None = Field(
        default=None, alias="inLanguage", description="Article language"
    )
    headline: NonEmptyString | None = Field(default=None, description="Article headline")
    description: NonEmptyString | None = Field(
        default=None, description="Article summary"
    )
    author: JsonLDEntity | list[JsonLDEntity] | None = Field(
        default=None, description="Article authors"
    )
    date_created: NonEmptyString | None = Field(
        default=None, alias="dateCreated", description="ISO 8601 creation date"
    )
    date_modified: NonEmptyString | None = Field(
        default=None, alias="dateModified", description="ISO 8601 modification date"
    )
    date_published: NonEmptyString | None = Field(
        default=None, alias="datePublished", description="ISO 8601 publication date"
    )
    about: JsonLDEntity | list[JsonLDEntity] | None = Field(
        default=None, description="Article topics"
    )
    mentions: JsonLDEntity | list[JsonLDEntity] | None = Field(
        default=None, description="Mentioned entities"
    )
    same_as: NonEmptyString | list[NonEmptyString] | None = Field(
        default=None, alias="sameAs", description="Related entity URLs"
    )
    publisher: JsonLDEntity | None = Field(default=None, description="Article publisher")

    @field_validator("date_created", "date_modified", "date_published")
    @classmethod
    def validate_date(cls, value: str | None) -> str | None:
        """Validate that date fields use ISO 8601 date or datetime format."""
        if value is not None:
            datetime.fromisoformat(value)
        return value


def unknown_json_ld_fields(
    data: dict[str, Any], model_type: type[BaseModel] = JsonLD, prefix: str = ""
) -> list[str]:
    """Return paths of unrecognized fields, including nested entities."""
    fields = {
        name: (field_name, field)
        for field_name, field in model_type.model_fields.items()
        for name in {field_name, field.alias or field_name}
    }
    nested_fields = {
        JsonLD: {
            "image": JsonLDImage, "is_part_of": JsonLDEntity, "author": JsonLDEntity,
            "about": JsonLDEntity, "mentions": JsonLDEntity,
            "publisher": JsonLDEntity,
        },
        JsonLDEntity: {"logo": JsonLDImage},
    }
    paths = []
    for key, value in data.items():
        path = f"{prefix}{key}"
        if key not in fields:
            paths.append(path)
            continue
        field_name, _ = fields[key]
        nested_type = nested_fields.get(model_type, {}).get(field_name)
        if nested_type and isinstance(value, dict):
            paths.extend(unknown_json_ld_fields(value, nested_type, f"{path}."))
        elif nested_type and isinstance(value, list):
            for index, item in enumerate(value):
                if isinstance(item, dict):
                    paths.extend(
                        unknown_json_ld_fields(item, nested_type, f"{path}[{index}].")
                    )
    return paths
