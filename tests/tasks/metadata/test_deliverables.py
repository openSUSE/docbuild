"""Unit tests for docbuild.tasks.metadata.deliverables."""

from pathlib import Path

from lxml import etree
import pytest

from docbuild.models.doctype import Doctype
from docbuild.tasks.metadata.deliverables import (
    collect_files_flat,
    get_deliverable_from_doctype,
)


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
    ids=["specific_doctype", "wildcard_doctype", "nonexistent_product", "nonexistent_lang"],
)
def test_get_deliverable_from_doctype(xmlconfig, doctype_str, expected_count, expected_ids):
    """Verify deliverables are correctly extracted for various doctypes."""
    if "nonexistent" in doctype_str:
        with pytest.raises(ValueError):
            Doctype.from_str(doctype_str)
        return

    doctype = Doctype.from_str(doctype_str)
    deliverables = get_deliverable_from_doctype(xmlconfig, doctype)

    assert len(deliverables) == expected_count
    if expected_ids:
        assert {d.docsuite for d in deliverables} == expected_ids


@pytest.mark.parametrize(
    "setup_files, doctype_str, expected_file_count",
    [
        (
            {"en-us/sles/15-SP4": ["DC-file1", "DC-file2", "ignored.xml"]},
            "sles/15-SP4/en-us",
            2,
        ),
        (
            {
                "en-us/sles/15-SP4": ["DC-file-foo", "DC-file-bar"],
                "de-de/sles/15-SP4": ["DC-file-foo", "DC-file-bar"],
            },
            "sles/15-SP4/en-us,de-de",
            4,
        ),
        ({}, "sles/15-SP4/en-us", 0),
    ],
    ids=["single_lang", "multi_lang", "no_files"],
)
def test_collect_files_flat(tmp_path: Path, setup_files, doctype_str, expected_file_count):
    """Verify that collect_files_flat finds DC-* files correctly."""
    cache_dir = tmp_path / "cache"
    for path_str, files in setup_files.items():
        dir_path = cache_dir / path_str
        dir_path.mkdir(parents=True, exist_ok=True)
        for f in files:
            (dir_path / f).touch()

    doctypes = [Doctype.from_str(doctype_str)]
    results = list(collect_files_flat(doctypes, cache_dir))

    assert len(results) == (1 if expected_file_count > 0 else 0)
    if results:
        _, _, found_files = results[0]
        assert len(found_files) == expected_file_count
