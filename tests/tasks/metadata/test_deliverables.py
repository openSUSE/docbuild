"""Unit tests for docbuild.tasks.metadata.deliverables."""


from lxml import etree
import pytest

from docbuild.models.doctype import Doctype
from docbuild.tasks.metadata.deliverables import get_deliverable_from_doctype


@pytest.fixture
def xmlconfig(request) -> etree.ElementTree:
    """Parse an XML string into an ElementTree.

    Accepts the XML string via ``@pytest.mark.parametrize`` indirect or
    falls back to an empty ``<docservconfig/>`` root.
    """
    xml_string = getattr(request, "param", None) or "<docservconfig/>"
    return etree.ElementTree(etree.fromstring(xml_string))


@pytest.mark.parametrize(
    "xmlconfig, doctype_str, expected_count, expected_ids",
    [
        (
            """
            <portal>
              <product xml:id="sles">
                <docset xml:id="sles.16-sp6" path="15-sp6">
                  <resources>
                    <locale lang="en-us">
                        <deliverable xml:id="sles.16-sp6.admin">
                            <dc file="DC-SLE-Micro-5.5-admin">
                                <format html="1"/>
                            </dc>
                        </deliverable>
                    </locale>
                  </resources>
                </docset>
              </product>
              <product xml:id="other">
                <docset xml:id="other.1.0" path="1.0">
                   <resources>
                     <locale lang="en-us">
                        <deliverable>
                            <dc file="DC-Micro-5.4-cockpit">
                                <format html="1"/>
                            </dc>
                        </deliverable>
                        <deliverable>
                            <dc file="DC-Micro-5.5-cockpit">
                                <format html="1"/>
                            </dc>
                        </deliverable>
                    </locale>
                   </resources>
                </docset>
              </product>
            </portal>
            """,
            "sles/15-sp6/en-us",
            1,
            {"sles/15-sp6/en-us:DC-SLE-Micro-5.5-admin"},
        ),
        (
            """
            <portal>
              <product xml:id="sles">
                <docset xml:id="sles.16-sp6" path="15-sp6">
                    <resources>
                        <locale lang="en-us">
                            <deliverable>
                                <dc file="DC-SLE-Micro-5.5-admin">
                                    <format html="1"/>
                                </dc>
                            </deliverable>
                        </locale>
                    </resources>
                </docset>
              </product>
              <product xml:id="other">
              <docset xml:id="other.1.0" path="1.0">
                  <resources>
                    <locale lang="en-us">
                      <deliverable>
                        <dc file="DC-Micro-5.4-cockpit">
                            <format html="1"/>
                        </dc>
                      </deliverable>
                    </locale>
                  </resources>
                </docset>
              </product>
            </portal>
            """,
            "//en-us",
            2,
            {
                "other/1.0/en-us:DC-Micro-5.4-cockpit",
                "sles/15-sp6/en-us:DC-SLE-Micro-5.5-admin",
            },
        ),
        ("<portal/>", "nonexistent/1.0/en-us", 0, set()),
        (
            """<portal>
                 <product xml:id='sles'>
                    <docset xml:id='sles.15-sp6' path="15-sp6" />
                 </product>
               </portal>""",
            "sles/15-sp6/de-de",
            0,
            set(),
        ),
    ],
    indirect=["xmlconfig"],
    ids=["specific_doctype", "wildcard_doctype", "nonexistent_product", "nonexistent_lang"],
)
def test_get_deliverable_from_doctype(xmlconfig, doctype_str, expected_count, expected_ids):
    """Verify deliverables are correctly extracted for various doctypes."""
    if "nonexistent" in doctype_str:
        with pytest.raises(ValueError):
            Doctype.from_str(doctype_str)
        return

    doctype = Doctype.from_str(doctype_str)
    deliverables = list(get_deliverable_from_doctype(xmlconfig, doctype))

    assert len(deliverables) == expected_count
    if expected_ids:
        assert {d.docsuite for d in deliverables} == expected_ids


def test_empty_locale_inherits_multiple_blueprints():
    """Verify empty locales inherit all blueprint deliverables in order."""
    xml_content = """
    <portal xmlns:xml="http://www.w3.org/XML/1998/namespace">
      <product xml:id="sles">
        <docset xml:id="sles.15-sp6" path="15-SP6">
          <resources>
            <locale lang="en-us">
              <deliverable xml:id="doc1"><dc file="DC-1"/></deliverable>
              <deliverable xml:id="doc2"><dc file="DC-2"/></deliverable>
            </locale>
            <locale lang="de-de"></locale>
          </resources>
        </docset>
      </product>
    </portal>
    """
    root = etree.ElementTree(etree.fromstring(xml_content))
    doctype = Doctype.from_str("sles/15-SP6/de-de")

    deliverables = list(get_deliverable_from_doctype(root, doctype))

    assert len(deliverables) == 2
    assert deliverables[0].xml.is_xref is True
    assert deliverables[0].xml.target_id == "doc1"
    assert deliverables[1].xml.is_xref is True
    assert deliverables[1].xml.target_id == "doc2"


def test_explicit_locale_ignores_blueprint():
    """Verify locales with explicit deliverables do not inherit from the blueprint."""
    xml_content = """
    <portal xmlns:xml="http://www.w3.org/XML/1998/namespace">
      <product xml:id="sles">
        <docset xml:id="sles.15-sp6" path="15-SP6">
          <resources>
            <locale lang="en-us">
              <deliverable xml:id="doc1"><dc file="DC-1"/></deliverable>
            </locale>
            <locale lang="de-de">
              <deliverable xml:id="de-doc"><dc file="DC-de"/></deliverable>
            </locale>
          </resources>
        </docset>
      </product>
    </portal>
    """
    root = etree.ElementTree(etree.fromstring(xml_content))
    doctype = Doctype.from_str("sles/15-SP6/de-de")

    deliverables = list(get_deliverable_from_doctype(root, doctype))

    assert len(deliverables) == 1
    assert deliverables[0].xml.is_xref is False
    assert deliverables[0].xml.deliverableid == "de-doc"


def test_independent_locale_handling():
    """Verify explicit and empty locales are handled independently in the same docset."""
    xml_content = """
    <portal xmlns:xml="http://www.w3.org/XML/1998/namespace">
      <product xml:id="sles">
        <docset xml:id="sles.15-sp6" path="15-SP6">
          <resources>
            <locale lang="en-us">
              <deliverable xml:id="doc1"><dc file="DC-1"/></deliverable>
            </locale>
            <locale lang="de-de"></locale>
            <locale lang="ja-jp">
              <deliverable xml:id="ja-doc"><dc file="DC-ja"/></deliverable>
            </locale>
          </resources>
        </docset>
      </product>
    </portal>
    """
    root = etree.ElementTree(etree.fromstring(xml_content))
    doctype = Doctype.from_str("sles/15-SP6/*")

    deliverables = list(get_deliverable_from_doctype(root, doctype))

    # We expect 3 deliverables total: en-us (explicit), de-de (inherited xref), ja-jp (explicit)
    assert len(deliverables) == 3

    # Check en-us
    assert deliverables[0].xml.deliverableid == "doc1"

    # Check de-de (synthetic xref)
    assert deliverables[1].xml.is_xref is True
    assert deliverables[1].xml.target_id == "doc1"

    # Check ja-jp (explicit)
    assert deliverables[2].xml.deliverableid == "ja-doc"
    assert deliverables[2].xml.is_xref is False
