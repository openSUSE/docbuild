from lxml import etree  # type: ignore
import pytest

from docbuild.config.xml.list import list_all_deliverables
from docbuild.models.doctype import Doctype


@pytest.fixture
def node() -> etree._ElementTree:
    """Fixture to create a mock XML node for testing."""
    xml_data = """<portal>
    <product id="sles" schemaversion="7.0">
        <docset path="15sp4" lifecycle="supported">
            <resources>
                <locale lang="en-us">
                    <deliverable>
                       <dc>DC-SLES-administration</dc>
                       <format epub="0" html="0" pdf="1" single-html="1"/>
                    </deliverable>
                    <deliverable>
                       <dc>DC-SLES-deployment</dc>
                       <format epub="0" html="0" pdf="1" single-html="1"/>
                    </deliverable>
                </locale>
                <locale lang="de-de">
                    <deliverable>
                       <dc>DC-SLES-administration</dc>
                    </deliverable>
                </locale>
            </resources>
        </docset>
        <docset path="15sp5" lifecycle="beta">
            <resources>
                <locale lang="en-us">
                    <deliverable category="installation-upgrade">
                       <dc>DC-SLES-autoyast</dc>
                       <format epub="0" html="0" pdf="1" single-html="1"/>
                    </deliverable>
                </locale>
            </resources>
        </docset>
    </product>
    </portal>
    """
    return etree.fromstring(xml_data, parser=None).getroottree()


@pytest.mark.parametrize(
    "doctypes, dc_files",
    [
        # 0
        (None, ["DC-SLES-administration", "DC-SLES-deployment", "DC-SLES-autoyast"]),
        # 1
        (
            [Doctype.from_str("*/*@supported,beta/en-us")],
            ["DC-SLES-administration", "DC-SLES-deployment", "DC-SLES-autoyast"],
        ),
        # 2
        (
            [Doctype.from_str("sles/*@supported,beta/en-us")],
            ["DC-SLES-administration", "DC-SLES-deployment", "DC-SLES-autoyast"],
        ),
        # 3
        (
            [Doctype.from_str("sles/*@supported,beta/en-us,de-de")],
            [
                "DC-SLES-administration",
                "DC-SLES-deployment",
                "DC-SLES-administration",
                "DC-SLES-autoyast",
            ],
        ),
        # 4
        (
            [Doctype.from_str("sles/15sp4,15sp5/en-us")],
            ["DC-SLES-administration", "DC-SLES-deployment", "DC-SLES-autoyast"],
        ),
        # 5
        (
            [Doctype.from_str("sles/*/*")],
            [
                "DC-SLES-administration",
                "DC-SLES-deployment",
                "DC-SLES-administration",
                "DC-SLES-autoyast",
            ],
        ),
        # 6
        (
            [Doctype.from_str("smart/*/en-us")],
            [],
        ),
    ],
)
def test_list_all_deliverables(
    doctypes: list[Doctype] | None,
    dc_files: list[str],
    node: etree._ElementTree,
) -> None:
    """Test the list_all_deliverables function with different doctypes."""
    deliverables = list(list_all_deliverables(node, doctypes))
    calc_dc_files = [d[0].text for d in deliverables]

    assert len(deliverables) == len(dc_files)
    assert calc_dc_files == dc_files
