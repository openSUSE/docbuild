"""Branch, subdir, and repository tests for deliverables."""

from lxml import etree  # type: ignore
import pytest

from docbuild.models.deliverable import Deliverable
from docbuild.models.deliverable.view import DeliverableXMLView
from docbuild.models.language import LanguageCode


def test_branch(first_deliverable: Deliverable) -> None:
    assert first_deliverable.branch == "maintenance/SLE15SP6"


def test_branch_property_fallback_locale() -> None:
    """Test that Deliverable.branch falls back to another locale if missing."""
    xml_content = """
    <docset>
        <resources>
            <locale lang="en-us">
                <deliverable type="dc" id="test"/>
            </locale>
            <locale lang="de-de">
                <branch>maintenance/SLE15SP6-fallback</branch>
            </locale>
        </resources>
    </docset>
    """
    node = etree.fromstring(xml_content).xpath("//locale[@lang='en-us']/deliverable")[0]
    deliverable = Deliverable(node)
    assert deliverable.branch == "maintenance/SLE15SP6-fallback"


def test_subdir(first_de_deliverable: Deliverable) -> None:
    assert first_de_deliverable.subdir == "l10n/sles/de-de"


def test_git_remote(first_deliverable: Deliverable) -> None:
    assert first_deliverable.git.url == "https://github.com/suse/doc-sle.git"


def test_missing_branch_raises(node: etree._ElementTree) -> None:
    for branch in node.xpath("//locale/branch"):
        branch.getparent().remove(branch)

    first_node = node.xpath("(/product | /portal/product)/docset/resources/locale/deliverable")[0]
    deliverable = Deliverable(first_node)

    with pytest.raises(ValueError, match="No branch found for this deliverable"):
        _ = deliverable.branch


def test_missing_git_raises(node: etree._ElementTree) -> None:
    git = node.xpath("(/product | /portal/product)/docset/resources/git")[0]
    git.getparent().remove(git)

    first_node = node.xpath(
        "(/product | /portal/product)/docset/resources/locale[@lang='en-us']/deliverable"
    )[0]
    deliverable = Deliverable(first_node)

    with pytest.raises(ValueError, match="No git remote found"):
        _ = deliverable.git


def test_xml_git_remote(first_deliverable: Deliverable) -> None:
    """Test the xml.git_remote() method directly."""
    assert first_deliverable.xml.git_remote() is not None
    assert first_deliverable.xml.git_remote().url == "https://github.com/suse/doc-sle.git"


def test_xml_git_remote_none(node: etree._ElementTree) -> None:
    """Test git_remote() returns None when <git> is missing."""
    git = node.xpath("(/product | /portal/product)/docset/resources/git")[0]
    git.getparent().remove(git)

    first_node = node.xpath(
        "(/product | /portal/product)/docset/resources/locale[@lang='en-us']/deliverable"
    )[0]
    deliverable = Deliverable(first_node)
    assert deliverable.xml.git_remote() is None


def test_xml_branch_method(first_deliverable: Deliverable) -> None:
    """Test the xml.branch() method directly."""
    assert first_deliverable.xml.branch() == "maintenance/SLE15SP6"


def test_xml_subdir_method(first_de_deliverable: Deliverable) -> None:
    """Test the xml.subdir() method directly."""
    assert first_de_deliverable.xml.subdir() == "l10n/sles/de-de"


def test_xml_subdir_empty(first_deliverable: Deliverable) -> None:
    """Test subdir() returns empty string when <subdir> is absent."""
    assert first_deliverable.xml.subdir() == ""


def test_xml_translations(ref_node, first_deliverable_from_lang) -> None:
    """Return translation info for ref locales pointing to a deliverable."""
    deliverable = first_deliverable_from_lang(ref_node, "en-us")
    translations = deliverable.xml.translation_infos()
    de_lang = LanguageCode(language="de-de")

    assert de_lang in translations
    info = translations[de_lang]
    assert info.lang == de_lang
    assert info.branch is None
    assert info.subdir is None


def test_deliverable_has_translation(ref_node, first_deliverable_from_lang) -> None:
    """Expose translations via the Deliverable facade."""
    deliverable = first_deliverable_from_lang(ref_node, "en-us")
    assert deliverable.has_translation("de-de") is True
    assert deliverable.has_translation("fr-fr") is False


def test_format_attrs_prebuilt_filters_unknown_url_formats() -> None:
    """Test unknown prebuilt URL format values are ignored."""
    xml_prebuilt = """
    <deliverable type="prebuilt">
        <prebuilt>
            <url format="html" href="https://example.com/html"/>
            <url format="other" href="https://example.com/xml"/>
        </prebuilt>
    </deliverable>
    """
    view = DeliverableXMLView(etree.fromstring(xml_prebuilt))
    assert view.format_attrs() == {
        "html": True,
        "pdf": False,
        "epub": False,
        "single-html": False,
    }


def test_format_attrs_unknown_kind() -> None:
    """Test format_attrs returns None for unknown deliverable kinds."""
    xml_unknown = """
    <deliverable type="unknown"></deliverable>
    """
    view = DeliverableXMLView(etree.fromstring(xml_unknown))
    assert view.format_attrs() is None


def test_format_attrs_dc_missing_format() -> None:
    """Test format_attrs returns None for DC deliverables missing <dc><format>."""
    xml_dc_no_format = """
    <deliverable type="dc">
        <dc file="DC-test">
          </dc>
    </deliverable>
    """
    view = DeliverableXMLView(etree.fromstring(xml_dc_no_format))
    assert view.format_attrs() is None


def test_xml_git_remote_fallback_invalid_url() -> None:
    """Test git_remote() gracefully falls back to string on invalid URLs."""
    xml_content = """
    <portal>
        <product id="p1">
            <docset path="d1">
                <resources>
                    <git remote="https://todo" />
                    <locale lang="en-us">
                        <deliverable id="test" />
                    </locale>
                </resources>
            </docset>
        </product>
    </portal>
    """
    node = etree.fromstring(xml_content).xpath("//deliverable")[0]
    view = DeliverableXMLView(node)

    # Should safely return the raw string instead of throwing a ValueError
    assert view.git_remote() == "https://todo"


def test_xml_translations() -> None:
    """Test translations property dynamically finds other locales."""
    xml_content = """
    <portal>
        <product id="p1">
            <docset path="d1">
                <resources>
                    <locale lang="en-us">
                        <deliverable id="test" />
                    </locale>
                    <locale lang="de-de">
                        <deliverable id="test_translation">
                            <ref linkend="test" />
                        </deliverable>
                    </locale>
                    <locale lang="ja-jp">
                        <deliverable id="other_doc" />
                    </locale>
                </resources>
            </docset>
        </product>
    </portal>
    """
    node = etree.fromstring(xml_content).xpath("//locale[@lang='en-us']/deliverable")[0]
    view = DeliverableXMLView(node)

    # Should find en-us and de-de, but ignore ja-jp since it doesn't reference 'test'
    assert view.translations == {"en-us", "de-de"}


def test_xml_category_title() -> None:
    """Test category_title safely resolves titles, names, and ID fallbacks."""
    xml_content = """
    <portal>
        <product id="p1">
            <categories>
                <category lang="en-us">
                  <language id="cat-title" title="Has Title Element" />
                  <language id="cat-name" title="Has Name Element" />
                </category>
            </categories>
            <docset path="d1">
                <resources>
                    <locale lang="en-us">
                        <deliverable id="d1" category="cat-title" />
                        <deliverable id="d2" category="cat-name" />
                        <deliverable id="d3" category="cat-missing" />
                        <deliverable id="d4" />
                    </locale>
                </resources>
            </docset>
        </product>
    </portal>
    """
    root = etree.fromstring(xml_content)
    d1 = DeliverableXMLView(root.xpath("//deliverable[@id='d1']")[0])
    d2 = DeliverableXMLView(root.xpath("//deliverable[@id='d2']")[0])
    d3 = DeliverableXMLView(root.xpath("//deliverable[@id='d3']")[0])
    d4 = DeliverableXMLView(root.xpath("//deliverable[@id='d4']")[0])

    assert d1.category_title == "Has Title Element"
    assert d2.category_title == "Has Name Element"
    assert d3.category_title == "cat-missing"  # Falls back to raw ID if not defined in <categories>
    assert d4.category_title is None           # No category assigned
