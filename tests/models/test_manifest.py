from datetime import date
from unittest.mock import Mock

from lxml import etree
import pytest

from docbuild.models.manifest import (
    Archive,
    Category,
    CategoryTranslation,
    Description,
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
        datemodified=date(2026, 1, 2),
    ).model_dump(by_alias=True)
    assert serialized["dateModified"] == "2026-01-02"


@pytest.mark.parametrize(
    "value, lang, expected",
    [
        ("11/04/2025", "en-us", date(2025, 11, 4)),
        ("11/04/2025", "de-de", date(2025, 4, 11)),
        ("2025/04/11", "ja-jp", date(2025, 4, 11)),
        ("2025.12.31", "fr-fr", date(2025, 12, 31)),
        ("11.03.2023", "de-de", date(2023, 3, 11)),
        ("11.3.2023",  "de-de", date(2023, 3, 11)),
        ("11/4/2025", "pt-br", date(2025, 4, 11)),
    ],
)
def test_single_document_parse_datemodified_locale(
    value: str, lang: str, expected: date
) -> None:
    """Parse dateModified using locale-based heuristics."""
    doc = SingleDocument.model_validate(
        {
            "dateModified": value,
            "lang": lang,
            "dcfile": "DC-TEST",
        }
    )
    assert doc.datemodified == expected


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


def test_description_serialize_lang() -> None:
    """Test serialization of LanguageCode"""
    desc = Description(lang="en-us", default=True, description="Test description")
    serialized = desc.model_dump(by_alias=True)
    assert serialized["lang"] == "en-us"


def test_category_translation_serialize_lang() -> None:
    """Test serialization of LanguageCode in CategoryTranslation."""
    cat_trans = CategoryTranslation(lang="de-de", default=False, title="Test Titel")
    serialized = cat_trans.model_dump()
    assert serialized["lang"] == "de-de"


def test_category_from_xml_node() -> None:
    """Test extraction of categories from an XML node."""
    doc = """<product>
        <category categoryid="cat1">
            <language lang="en-us" default="1" title="Category 1 EN"/>
            <language lang="de-de" title="Kategorie 1 DE"/>
        </category>
        <categories>
            <category categoryid="cat2">
                <language lang="fr-fr" title="Catégorie 2 FR"/>
            </category>
        </categories>
        <category categoryid="cat3_no_lang"/>
        <category> <!-- missing categoryid -->
            <language lang="en-us" title="No ID"/>
        </category>
    </product>
    """
    node = etree.fromstring(doc, parser=None)
    mock_deliverable = Mock()
    mock_deliverable.xml.categories.return_value = list(node.xpath("category|categories/category"))

    # Reset class variable for predictable rank
    Category.reset_rank()
    models = list(Category.from_xml_node(mock_deliverable))

    assert len(models) == 4

    # Test first category
    assert models[0].id == "cat1"
    assert models[0].rank == 1
    assert len(models[0].translations) == 2
    assert models[0].translations[0].lang == "en-us"
    assert models[0].translations[0].default is True
    assert models[0].translations[0].title == "Category 1 EN"

    # Test category with missing categoryid attribute
    assert models[3].id == ""
    assert models[3].rank == 4
    assert models[3].translations[0].title == "No ID"


def test_category_rank() -> None:
    # Just to be sure, we reset the current rank:
    Category.reset_rank()
    for idx, i in enumerate(["A", "B", "C"], 1):
        cat = Category(id=i, translations=[])
        serizalized = cat.model_dump()
        assert serizalized["rank"] == idx


def test_archive_serialize_lang() -> None:
    """Test serialization of LanguageCode in Archive."""
    archive = Archive(lang="fr-fr", default=False, zip="test.zip")
    serialized = archive.model_dump()
    assert serialized["lang"] == "fr-fr"


def test_description_from_xml_node() -> None:
    """Test extraction of descriptions from XML node"""
    doc = """<docservconfig>
        <desc default="1" lang="en-us">
            <title>Hello Title</title>
            <p>Hello Description</p>
        </desc>
        <product productid="sles" schemaversion="6.0">
          <!-- content doesn't matter here -->
        </product>
    </docservconfig>
    """
    node = etree.fromstring(doc, parser=None)
    mock_deliverable = Mock()
    mock_deliverable.xml.desc.return_value = list(node.xpath("desc"))
    model = next(iter(Description.from_xml_node(mock_deliverable)))
    serialized = model.model_dump(by_alias=True)
    assert serialized == {
        "lang": "en-us",
        "default": True,
        "description": "<p>Hello Description</p>",
    }
