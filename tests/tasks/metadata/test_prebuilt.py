"""Tests for the prebuilt (Antora) metadata extractor."""

import json
from pathlib import Path
from unittest.mock import MagicMock

from lxml import etree  # type: ignore
import pytest

from docbuild.tasks.metadata.prebuilt import extract_prebuilt_metadata


@pytest.fixture
def mock_deliverable():
    """Create a mock Deliverable with a fully populated XML node."""
    xml_content = b"""
    <deliverable gated="true" category="cloud-native">
        <description>Test description for admission controller.</description>
        <prebuilt>
            <title>SUSE Security Admission Controller</title>
            <url format="html" href="/admission-controller/latest/en/index.html"/>
            <url format="pdf" href="/admission-controller/latest/en/admission-controller.pdf"/>
        </prebuilt>
    </deliverable>
    """
    node = etree.fromstring(xml_content)

    mock_dev = MagicMock()
    mock_dev._node = node
    # Mock the LanguageCode stringification
    mock_dev.xml.lang.__str__.return_value = "en-us"
    return mock_dev


def test_extract_prebuilt_metadata_success(tmp_path: Path, mock_deliverable: MagicMock):
    """Test full extraction when XML and HTML JSON-LD are both present."""
    # 1. Setup the dummy HTML file in the expected temporary path
    html_dir = tmp_path / "en-us" / "admission-controller" / "latest" / "en"
    html_dir.mkdir(parents=True)
    html_file = html_dir / "index.html"

    # Provide the sample JSON-LD inside a script block
    json_ld_payload = {
        "@context": "https://schema.org",
        "@type": "TechArticle",
        "headline": "What is SUSE Security Admission Controller?",
        "inLanguage": "en",
        "dateModified": "2026-06-18T12:00:00Z",
        "mentions": [
            {
                "@type": "SoftwareApplication",
                "name": "SUSE Security Admission Controller",
                "softwareVersion": "1.37",
            }
        ]
    }

    html_file.write_text(
        f"""
        <html>
        <head>
            <script type="application/ld+json">
            {json.dumps(json_ld_payload)}
            </script>
        </head>
        <body>Hello</body>
        </html>
        """,
        encoding="utf-8"
    )

    # 2. Run the extractor
    result = extract_prebuilt_metadata(mock_deliverable, tmp_path)

    # 3. Assert correct mapping of XML and JSON-LD
    assert result["isGated"] is True
    assert result["category"] == "cloud-native"

    doc = result["docs"][0]
    assert doc["description"] == "Test description for admission controller."
    assert doc["title"] == "What is SUSE Security Admission Controller?"
    assert doc["dateModified"] == "2026-06-18"  # Should strip the time
    assert doc["lang"] == "en-us"  # Should expand 'en' to 'en-us'
    assert doc["default"] is True

    assert doc["format"]["html"] == "/admission-controller/latest/en/index.html"
    assert doc["format"]["pdf"] == "/admission-controller/latest/en/admission-controller.pdf"

    # Tasks and Products mapping
    assert "SUSE Security Admission Controller" in result["tasks"]
    assert len(result["products"]) == 1
    assert result["products"][0]["name"] == "SUSE Security Admission Controller"
    assert result["products"][0]["versions"] == ["1.37"]


def test_extract_prebuilt_metadata_missing_html(tmp_path: Path, mock_deliverable: MagicMock):
    """Test extraction gracefully handles missing HTML files."""
    # Run extractor WITHOUT creating the HTML file in tmp_path
    result = extract_prebuilt_metadata(mock_deliverable, tmp_path)

    # Should still extract XML properties safely
    assert result["isGated"] is True
    assert result["category"] == "cloud-native"

    doc = result["docs"][0]
    assert doc["description"] == "Test description for admission controller."
    assert doc["format"]["html"] == "/admission-controller/latest/en/index.html"

    # JSON properties should fall back to empty defaults gracefully
    assert doc["title"] == ""
    assert doc["dateModified"] == ""
    assert result["tasks"] == []


def test_extract_prebuilt_metadata_no_json_ld(tmp_path: Path, mock_deliverable: MagicMock):
    """Test extraction gracefully handles HTML files missing the JSON-LD tag."""
    html_dir = tmp_path / "en-us" / "admission-controller" / "latest" / "en"
    html_dir.mkdir(parents=True)
    html_file = html_dir / "index.html"

    # Write HTML without the script tag
    html_file.write_text("<html><head><title>Test</title></head></html>", encoding="utf-8")

    result = extract_prebuilt_metadata(mock_deliverable, tmp_path)

    # Should safely return with empty JSON fallbacks
    doc = result["docs"][0]
    assert doc["title"] == ""
    assert result["tasks"] == []
