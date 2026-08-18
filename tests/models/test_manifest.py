from datetime import date

from lxml import etree
import pytest

from docbuild.models.language import LanguageCode
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


def test_description_default_for_english_when_missing() -> None:
    """Auto-set default=True when lang is en-us and default is omitted."""
    desc = Description(lang="en-us", description="Test description")
    assert desc.default is True


def test_description_explicit_default_is_preserved() -> None:
    """Do not override an explicitly provided default value."""
    desc = Description(lang="en-us", default=False, description="Test description")
    assert desc.default is False


def test_category_translation_serialize_lang() -> None:
    """Test serialization of LanguageCode in CategoryTranslation."""
    cat_trans = CategoryTranslation(lang="de-de", default=False, title="Test Titel")
    serialized = cat_trans.model_dump()
    assert serialized["lang"] == "de-de"


def test_category_translation_default_for_english_when_missing() -> None:
    """Auto-set default=True when lang is en-us and default is omitted."""
    cat_trans = CategoryTranslation(lang="en-us", title="About")
    assert cat_trans.default is True


def test_category_translation_explicit_default_is_preserved() -> None:
    """Do not override an explicitly provided default value."""
    cat_trans = CategoryTranslation(lang="en-us", default=False, title="About")
    assert cat_trans.default is False


def test_category_from_xml_node() -> None:
    """Test extraction of categories from an XML node (portal schema v7)."""
    doc = """<product>
        <categories>
            <category lang="en-us">
                <language id="cat.about" title="About" default="1"/>
                <language id="cat.deployment" title="Deployment"/>
            </category>
            <category lang="de-de">
                <language linkend="cat.about" title="Über"/>
                <language linkend="cat.deployment" title="Bereitstellung"/>
            </category>
        </categories>
    </product>
    """
    node = etree.fromstring(doc, parser=None)
    Category.reset_rank()
    models = list(Category.from_xml_node(node))

    assert len(models) == 2

    # cat.about has three translations
    assert models[0].id == "cat.about"
    assert models[0].rank == 1
    assert len(models[0].translations) == 2
    assert models[0].translations[0].lang == "en-us"
    assert models[0].translations[0].default is True
    assert models[0].translations[0].title == "About"
    assert models[0].translations[1].lang == "de-de"
    assert models[0].translations[1].title == "Über"

    # cat.deployment has two translations
    assert models[1].id == "cat.deployment"
    assert models[1].rank == 2
    assert len(models[1].translations) == 2
    assert models[1].translations[0].default is True
    assert models[1].translations[1].default is False

    # languages with neither id nor linkend are skipped (line 164 coverage)
    doc_no_id = """<product>
        <categories>
            <category lang="en-us">
                <language title="No ID"/>
            </category>
        </categories>
    </product>"""
    Category.reset_rank()
    assert list(Category.from_xml_node(etree.fromstring(doc_no_id))) == []


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


def test_archive_zip_is_autogenerated_when_omitted() -> None:
    """Build archive zip path from lang/product/docset when zip is omitted."""
    archive = Archive(lang="en-us", product="sles", docset="15-SP7")

    assert archive.zip == "/en-us/sles/15-SP7/sles-15-SP7-en-us.zip"


def test_archive_requires_context_when_zip_is_omitted() -> None:
    """Raise a validation error when zip and required context are missing."""
    with pytest.raises(ValueError, match=r"Argument 'zip' is required"):
        Archive(lang="en-us")


def test_description_from_xml_node() -> None:
    """Test extraction of descriptions from XML node (direct and wrapped)."""
    # Schema v7: desc nested inside <descriptions>
    doc = """<product>
        <descriptions>
            <desc default="1" lang="en-us">
                <title>Hello Title</title>
                <p>Hello Description</p>
            </desc>
            <desc lang="de-de">
                <title>Hallo Titel</title>
                <p>Hallo Beschreibung</p>
            </desc>
        </descriptions>
    </product>
    """
    node = etree.fromstring(doc, parser=None)
    models = list(Description.from_xml_node(node))
    assert len(models) == 2
    serialized = models[0].model_dump(by_alias=True)
    assert serialized == {
        "lang": "en-us",
        "default": True,
        "description": "<p>Hello Description</p>",
    }
    assert models[1].lang == LanguageCode(language="de-de")


def test_description_from_xml_node_marks_english_default() -> None:
    """Descriptions without a default attribute mark en-us as the default."""
    doc = """<product>
        <descriptions>
            <desc lang="en-us"><p>English</p></desc>
            <desc lang="de-de"><p>German</p></desc>
            <desc default="0" lang="en-us"><p>Not default</p></desc>
        </descriptions>
    </product>
    """
    models = list(Description.from_xml_node(etree.fromstring(doc, parser=None)))

    assert [m.default for m in models] == [True, False, False]


def test_single_document_warn_missing_title(caplog: pytest.LogCaptureFixture) -> None:
    """warn_missing_title logs a warning when title is None or empty (line 261 coverage)."""
    import logging

    with caplog.at_level(logging.WARNING):
        SingleDocument(dcfile="DC-FOO", lang="en-us", title="")

    assert any("DC-FOO" in r.message for r in caplog.records)
    assert any("missing title" in r.message.lower() for r in caplog.records)


def test_single_document_serialize_date_none() -> None:
    """serialize_date returns an empty string when datemodified is None (line 271 coverage)."""
    serialized = SingleDocument(
        lang="en",
        title="A title",
        dcfile="DC-BAR",
        format=DocumentFormat(html="/html"),
    ).model_dump(by_alias=True)
    assert serialized["dateModified"] == ""
