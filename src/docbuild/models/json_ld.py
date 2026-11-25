"""Pydantic model for validating JSON-LD metadata embedded in HTML."""

from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

NonEmptyString = Annotated[str, StringConstraints(strict=True, min_length=1)]


class JSON_LD(BaseModel):  # noqa: N801
    """JSON-LD metadata used for an article."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    name: NonEmptyString | None = Field(default=None, description="Article title")
    description: NonEmptyString | None = Field(
        default=None, description="Article summary"
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

    @field_validator("date_created", "date_modified", "date_published")
    @classmethod
    def validate_date(cls, value: str | None) -> str | None:
        """Validate that date fields use ISO 8601 date or datetime format."""
        if value is not None:
            if "T" in value:
                datetime.fromisoformat(value)
            else:
                date.fromisoformat(value)
        return value
