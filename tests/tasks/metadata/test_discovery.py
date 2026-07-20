"""Tests for metadata deliverable discovery helpers."""

from lxml import etree
import pytest

from docbuild.models.doctype import Doctype
from docbuild.tasks.metadata.discovery import (
    get_deliverables_for_doctype,
    iter_doctype_groups,
)


@pytest.mark.parametrize(
    "xmlconfig, doctype_str, expected_count, expected_ids",
    [
        (
            """
            <portal>
              <product id="sles">
                <docset id="sles.16-sp6" path="15-sp6">
                  <resources>
                    <locale lang="en-us">
                        <deliverable id="sles.16-sp6.admin">
                            <dc file="DC-SLE-Micro-5.5-admin">
                                <format html="1"/>
                            </dc>
                        </deliverable>
                    </locale>
                  </resources>
                </docset>
              </product>
              <product id="other">
                <docset id="other.1.0" path="1.0">
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
              <product id="sles">
                <docset id="sles.16-sp6" path="15-sp6">
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
              <product id="other">
                <docset id="other.1.0" path="1.0">
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
                 <product id='sles'>
                    <docset id='sles.15-sp6' path="15-sp6" />
                 </product>
               </portal>""",
            "sles/15-sp6/de-de",
            0,
            set(),
        ),
    ],
    indirect=["xmlconfig"],
    ids=[
        "specific_doctype",
        "wildcard_doctype",
        "nonexistent_product",
        "nonexistent_lang",
    ],
)
def test_get_deliverables_for_doctype(
    xmlconfig,
    doctype_str,
    expected_count,
    expected_ids,
):
    """Verify deliverables are correctly extracted for various doctypes."""
    if "nonexistent" in doctype_str:
        with pytest.raises(ValueError):
            Doctype.from_str(doctype_str)
        return

    doctype = Doctype.from_str(doctype_str)
    deliverables = list(get_deliverables_for_doctype(xmlconfig, doctype))

    assert len(deliverables) == expected_count
    if expected_ids:
        assert {deliverable.docsuite for deliverable in deliverables} == expected_ids


class TestIterDoctypeGroups:
    """Tests for iter_doctype_groups."""

    def test_iter_doctype_groups_returns_grouped_deliverables(self) -> None:
        """Ensure deliverables are grouped by product and docset."""
        xml_string = """
        <portal>
          <product id="sles">
            <docset id="sles.16-sp6" path="15-sp6">
              <resources>
                <locale lang="en-us">
                    <deliverable>
                        <dc file="DC-SLE-Micro-5.5-admin">
                            <format html="1"/>
                        </dc>
                    </deliverable>
                    <deliverable>
                        <dc file="DC-SLE-Micro-5.6-admin">
                            <format html="1"/>
                        </dc>
                    </deliverable>
                </locale>
              </resources>
            </docset>
          </product>
        </portal>
        """
        root = etree.ElementTree(etree.fromstring(xml_string))
        doctype = Doctype.from_str("sles/15-sp6/en-us")

        groups = list(iter_doctype_groups(root, [doctype]))

        assert len(groups) == 1
        product, docset, deliverables = groups[0]
        assert product == "sles"
        assert docset == "15-sp6"
        assert len(deliverables) == 2

    def test_iter_doctype_groups_wildcard_docset(self) -> None:
        """Wildcard doctypes should return one group per docset."""
        xml_string = """
        <portal>
          <product id="smart">
            <docset id="smart.deploy" path="deploy-upgrade">
              <resources>
                <locale lang="en-us">
                    <deliverable>
                        <dc file="DC-a">
                            <format html="1"/>
                        </dc>
                    </deliverable>
                </locale>
              </resources>
            </docset>
            <docset id="smart.ops" path="operations-guide">
              <resources>
                <locale lang="en-us">
                    <deliverable>
                        <dc file="DC-b">
                            <format html="1"/>
                        </dc>
                    </deliverable>
                </locale>
              </resources>
            </docset>
          </product>
        </portal>
        """
        root = etree.ElementTree(etree.fromstring(xml_string))
        doctype = Doctype.from_str("smart/*/en-us")

        groups = list(iter_doctype_groups(root, [doctype]))
        docsets = {docset for _, docset, _ in groups}

        assert docsets == {"deploy-upgrade", "operations-guide"}


def test_get_deliverables_for_doctype_skips_non_dc_nodes() -> None:
    """Only DC deliverables should be yielded when nodes are mixed."""
    xml_string = """
    <portal>
      <product id="smart">
        <docset id="smart.deploy" path="deploy-upgrade">
          <resources>
            <locale lang="en-us">
              <deliverable>
                <dc file="DC-first-doc">
                  <format html="1"/>
                </dc>
              </deliverable>
                <deliverable type="prebuilt">
                    <prebuilt format="pdf"/>
                </deliverable>
                <deliverable>
                    <dc file="DC-actual-doc">
                        <format html="1"/>
                    </dc>
                </deliverable>
            </locale>
          </resources>
        </docset>
      </product>
    </portal>
    """
    root = etree.ElementTree(etree.fromstring(xml_string))
    doctype = Doctype.from_str("smart/deploy-upgrade/en-us")

    deliverables = list(get_deliverables_for_doctype(root, doctype))

    assert [d.xml.dcfile for d in deliverables] == ["DC-first-doc", "DC-actual-doc"]
