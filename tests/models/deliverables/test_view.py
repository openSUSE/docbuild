"""Branch, subdir, and repository tests for deliverables."""

from lxml import etree
import pytest

from docbuild.models.deliverable import Deliverable
from docbuild.models.deliverable.view import DeliverableXMLView


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
          <!-- no <format /> -->
        </dc>
    </deliverable>
    """
    view = DeliverableXMLView(etree.fromstring(xml_dc_no_format))
    assert view.format_attrs() is None
