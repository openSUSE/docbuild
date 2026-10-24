"""Branch, subdir, and repository tests for deliverables."""

from lxml import etree  # type: ignore
import pytest

from docbuild.constants import XML_ID
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
                <deliverable type="dc" xml:id="test"/>
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

    first_node = node.xpath(
        "(/product | /portal/product)/docset/resources/locale/deliverable"
    )[0]
    deliverable = Deliverable(first_node)

    with pytest.raises(ValueError, match="No branch found for this deliverable"):
        _ = deliverable.branch


def test_missing_git_returns_none(node: etree._ElementTree) -> None:
    """Test that a deliverable without a git node safely returns None."""
    git_node = node.xpath("(/product | /portal/product)/docset/resources/git")[0]
    git_node.getparent().remove(git_node)

    first_node = node.xpath(
        "(/product | /portal/product)/docset/resources/locale[@lang='en-us']/deliverable"
    )[0]
    deliverable = Deliverable(first_node)

    assert deliverable.git is None
    assert deliverable.has_git_repo is False


def test_xml_git_remote(first_deliverable: Deliverable) -> None:
    """Test the xml.git_remote() method directly."""
    assert first_deliverable.xml.git_remote() is not None
    assert (
        first_deliverable.xml.git_remote().url == "https://github.com/suse/doc-sle.git"
    )


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


def test_subdir_combined(
    first_ref_deliverable_with_subdir: Deliverable,
) -> None:
    """Test that locale and deliverable subdirs are combined."""
    assert first_ref_deliverable_with_subdir.subdir == "l10n/sles/de-de/guide"


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
        <product xml:id="p1">
            <docset path="d1">
                <resources>
                    <git remote="https://todo" />
                    <locale lang="en-us">
                        <deliverable xml:id="test" />
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
        <product xml:id="p1">
            <docset path="d1">
                <resources>
                    <locale lang="en-us">
                        <deliverable xml:id="test" />
                    </locale>
                    <locale lang="de-de">
                        <deliverable xml:id="test_translation">
                            <xref linkend="test" />
                        </deliverable>
                    </locale>
                    <locale lang="ja-jp">
                        <deliverable xml:id="other_doc" />
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


def test_xml_translations_no_docset() -> None:
    """Test translations property with a node that has no docset."""
    xml_content = """
    <portal>
        <product xml:id="p1">
            <docset path="d1">
                <resources>
                    <locale lang="en-us">
                        <deliverable xml:id="test" />
                    </locale>
                </resources>
            </docset>
        </product>
    </portal>
    """
    node = etree.fromstring(xml_content).xpath("//deliverable")[0]
    view = DeliverableXMLView(node)
    assert view.translations == {"en-us"}


def test_xml_translations_no_lang_in_locale() -> None:
    """Test translations property with a locale that has no lang attribute."""
    xml_content = """
    <portal>
        <product xml:id="p1">
            <docset path="d1">
                <resources>
                    <locale lang="en-us">
                        <deliverable xml:id="test" />
                    </locale>
                    <locale> <!-- No lang attribute -->
                        <deliverable xml:id="test_translation">
                            <xref linkend="test" />
                        </deliverable>
                    </locale>
                </resources>
            </docset>
        </product>
    </portal>
    """
    node = etree.fromstring(xml_content).xpath("//locale[@lang='en-us']/deliverable")[0]
    view = DeliverableXMLView(node)
    assert view.translations == {"en-us"}


def test_xml_category_title() -> None:
    """Test category_title safely resolves titles, names, and ID fallbacks."""
    xml_content = """
    <portal>
        <product xml:id="p1">
            <categories>
                <category lang="en-us">
                  <language xml:id="cat-title">
                    <title>Has Title Element</title>
                  </language>
                  <language xml:id="cat-title-attr" title="Has Title Attribute" />
                  <language xml:id="cat-name" name="Has Name Element" />
                </category>
            </categories>
            <docset path="d1">
                <resources>
                    <locale lang="en-us">
                        <deliverable xml:id="d1" category="cat-title" />
                        <deliverable xml:id="d1b" category="cat-title-attr" />
                        <deliverable xml:id="d2" category="cat-name" />
                        <deliverable xml:id="d3" category="cat-missing" />
                        <deliverable xml:id="d4" />
                    </locale>
                </resources>
            </docset>
        </product>
    </portal>
    """
    root = etree.fromstring(xml_content)
    d1 = DeliverableXMLView(root.xpath("//deliverable[@xml:id='d1']")[0])
    d1b = DeliverableXMLView(root.xpath("//deliverable[@xml:id='d1b']")[0])
    d2 = DeliverableXMLView(root.xpath("//deliverable[@xml:id='d2']")[0])
    d3 = DeliverableXMLView(root.xpath("//deliverable[@xml:id='d3']")[0])
    d4 = DeliverableXMLView(root.xpath("//deliverable[@xml:id='d4']")[0])

    assert d1.category_title == "Has Title Element"
    assert d1b.category_title == "Has Title Attribute"
    assert d2.category_title == "Has Name Element"
    assert (
        d3.category_title == "cat-missing"
    )  # Falls back to raw ID if not defined in <categories>
    assert d4.category_title is None  # No category assigned


def test_xref_recursive_resolution() -> None:
    """Test recursive target resolution for xref deliverables."""
    xml_content = """
    <portal>
        <product xml:id="p1">
            <docset path="d1">
                <resources>
                    <locale lang="en-us">
                        <deliverable xml:id="target-dc" type="dc">
                            <dc file="DC-target">
                                <format html="1" pdf="1" />
                            </dc>
                        </deliverable>
                        <deliverable xml:id="mid-xref" type="xref">
                            <xref linkend="target-dc" />
                        </deliverable>
                    </locale>
                    <locale lang="de-de">
                        <deliverable xml:id="de-xref" type="xref">
                            <xref linkend="mid-xref" />
                        </deliverable>
                    </locale>
                </resources>
            </docset>
        </product>
    </portal>
    """
    root = etree.fromstring(xml_content)
    de_node = root.xpath("//deliverable[@xml:id='de-xref']")[0]
    view = DeliverableXMLView(de_node)

    assert view.is_xref is True
    assert view.target_node is not None
    assert view.target_node.get(XML_ID) == "mid-xref"
    assert view.final_target_node is not None
    assert view.final_target_node.get(XML_ID) == "target-dc"
    assert view.dcfile == "DC-target"
    assert view.target_id == "mid-xref"
    assert view.format_attrs() == {
        "html": True,
        "pdf": True,
        "epub": False,
        "single-html": False,
    }


def test_xref_circular_and_broken() -> None:
    """Test target_node and final_target_node handling of cycles and broken links."""
    xml_content = """
    <portal>
        <product xml:id="p1">
            <docset path="d1">
                <resources>
                    <locale lang="en-us">
                        <deliverable xml:id="cycle-a" type="xref">
                            <xref linkend="cycle-b" />
                        </deliverable>
                        <deliverable xml:id="cycle-b" type="xref">
                            <xref linkend="cycle-a" />
                        </deliverable>
                        <deliverable xml:id="broken-xref" type="xref">
                            <xref linkend="non-existent" />
                        </deliverable>
                        <deliverable xml:id="not-an-xref" type="dc">
                            <dc file="DC-test" />
                        </deliverable>
                    </locale>
                </resources>
            </docset>
        </product>
    </portal>
    """
    root = etree.fromstring(xml_content)

    view_a = DeliverableXMLView(root.xpath("//deliverable[@xml:id='cycle-a']")[0])
    assert view_a.final_target_node is not None  # Cycle handled without infinite loop

    view_broken = DeliverableXMLView(root.xpath("//deliverable[@xml:id='broken-xref']")[0])
    assert view_broken.target_node is None
    assert view_broken.final_target_node is None

    view_not_xref = DeliverableXMLView(root.xpath("//deliverable[@xml:id='not-an-xref']")[0])
    assert view_not_xref.is_xref is False
    assert view_not_xref.target_node is None
    assert view_not_xref.final_target_node is view_not_xref.node


def test_xref_to_prebuilt_formats_and_category() -> None:
    """Test format resolution and category extraction for xrefs to prebuilt deliverables."""
    xml_content = """
    <portal>
        <product xml:id="p1">
            <categories>
                <category lang="en-us">
                    <language xml:id="cat1">
                        <title>Category One</title>
                    </language>
                    <language xml:id="cat2">
                        <title>Category Two</title>
                    </language>
                </category>
            </categories>
            <docset path="d1">
                <resources>
                    <locale lang="en-us">
                        <deliverable xml:id="pb-target" type="prebuilt" category="cat1">
                            <prebuilt>
                                <title>Prebuilt Title</title>
                                <url format="html" href="/cloudnative/en/index.html"/>
                                <url format="pdf" href="/cloudnative/en/guide.pdf"/>
                            </prebuilt>
                        </deliverable>
                    </locale>
                    <locale lang="de-de">
                        <deliverable xml:id="pb-xref-inherit" type="xref">
                            <xref linkend="pb-target"/>
                        </deliverable>
                        <deliverable xml:id="pb-xref-override" type="xref">
                            <xref linkend="pb-target" category="cat2"/>
                        </deliverable>
                    </locale>
                </resources>
            </docset>
        </product>
    </portal>
    """
    root = etree.fromstring(xml_content)

    inherit_node = root.xpath("//deliverable[@xml:id='pb-xref-inherit']")[0]
    inherit_deliv = Deliverable(inherit_node)
    assert inherit_deliv.xml.is_xref is True
    assert inherit_deliv.xml.is_prebuilt is True
    assert inherit_deliv.xml.categoryid == "cat1"
    assert inherit_deliv.xml.category_title == "Category One"
    assert inherit_deliv.xml.format_attrs() == {
        "epub": False,
        "html": True,
        "pdf": True,
        "single-html": False,
    }
    assert inherit_deliv.format == {
        "epub": False,
        "html": True,
        "pdf": True,
        "single-html": False,
    }

    override_node = root.xpath("//deliverable[@xml:id='pb-xref-override']")[0]
    override_deliv = Deliverable(override_node)
    assert override_deliv.xml.categoryid == "cat2"
    assert override_deliv.xml.category_title == "Category Two"
