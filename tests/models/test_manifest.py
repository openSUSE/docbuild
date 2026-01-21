from datetime import date

import pytest

from docbuild.models.manifest import (
    Document,
    DocumentFormat,
    SingleDocument,
)


@pytest.mark.parametrize(
    "data,expected",
    [
        # 1: Full data
        (
            {
                "html": "/html-path",
                "pdf": "/pdf-path",
                "single-html": "/single-html-path",
            },
            #
            {
                "html": "/html-path",
                "pdf": "/pdf-path",
                "single-html": "/single-html-path",
            },
        ),
        # 2: Only required field
        (
            {
                "html": "/html-path",
            },
            #
            {
                "html": "/html-path",
            },
        ),
        # 3: Optional pdf field is empty string
        (
            {
                "html": "/html-path",
                "pdf": "",
            },
            #
            {
                "html": "/html-path",
            },
        ),
        # 4: Optional single-html field is empty string
        (
            {
                "html": "/html-path",
                "single-html": "",
            },
            #
            {
                "html": "/html-path",
            },
        ),
        # 5: Optional pdf field is None
        (
            {
                "html": "/html-path",
                "pdf": None,
            },
            #
            {
                "html": "/html-path",
            },
        ),
    ],
)
def test_manifest_documentformat(data, expected):
    """Test DocumentFormat model serialization and deserialization."""

    doc = DocumentFormat.model_validate(data)
    serialized = doc.model_dump(by_alias=True)
    assert serialized == expected


def test_single_document_serialize_date_non_none() -> None:
    """Serialize datemodified with a non-None date value."""

    serialized = SingleDocument(
        lang="en",
        title="Example title",
        description="Example description",
        dcfile="DC-EXAMPLE",
        format=DocumentFormat(html="/example-html"),
        datemodified=date(2025, 1, 2),
    ).model_dump(by_alias=True)
    assert serialized["dateModified"] == "2025-01-02"


@pytest.mark.parametrize(
    "input_rank, expected_internal, expected_serialized",
    [
        ("", None, ""),  # empty string → None → ""
        ("  ", None, ""),  # whitespace-only → None → ""
        (None, None, ""),  # explicit None → None → ""
        ("5", 5, "5"),  # string number → int → "5"
        (5, 5, "5"),  # int stays int → "5"
    ],
)
def test_document_rank_coercion_and_serialization(
    input_rank: str | int | None,
    expected_internal: int | None,
    expected_serialized: str,
) -> None:
    """Coerce rank values and serialize using the custom validator/serializer."""

    doc = Document(rank=input_rank)

    # internal Python representation after validation
    assert doc.rank == expected_internal

    # serialized representation used in manifests
    serialized = doc.model_dump(by_alias=True)
    # rank has no alias, so its key is "rank"
    assert serialized["rank"] == expected_serialized
