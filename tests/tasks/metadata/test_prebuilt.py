"""Tests for the prebuilt (Antora) metadata extractor."""

import json
from pathlib import Path

from lxml import etree  # type: ignore
import pytest

from docbuild.models.deliverable import Deliverable
from docbuild.tasks.metadata.prebuilt import extract_prebuilt_metadata


@pytest.fixture
def mock_deliverable():
    """Create a real Deliverable with a fully populated XML node."""
    xml_content = b"""
    <portal schemaversion="7.0">
        <product id="cloudnative">
            <name>Test Product</name>
            <acronym>TP</acronym>
            <docset lifecycle="supported" id="cloudnative.admission-controller" path="admission-controller">
              <version>1.37</version>
              <resources>
                <locale lang="en-us">
                  <deliverable gated="true" category="cloud-native" id="test-id">
                      <prebuilt>
                          <title>SUSE Security Admission Controller</title>
                          <url format="html" href="/admission-controller/latest/en/index.html"/>
                          <url format="pdf" href="/admission-controller/latest/en/admission-controller.pdf"/>
                          <descriptions>
                            <desc lang="en-us">Test description for admission controller.</desc>
                          </descriptions>
                      </prebuilt>
                  </deliverable>
                </locale>
              </resources>
            </docset>
        </product>
    </portal>
    """
    root = etree.fromstring(xml_content)
    # Instantiate a real Deliverable object from the deeply nested node
    node = root.xpath("//deliverable")[0]
    return Deliverable(node)


def test_extract_prebuilt_metadata_success(tmp_path: Path, mock_deliverable: Deliverable):
    """Test full extraction when XML and HTML JSON-LD are both present."""
    html_dir = tmp_path / "en-us" / "admission-controller" / "latest" / "en"
    html_dir.mkdir(parents=True)
    html_file = html_dir / "index.html"

    # Provide the realistic JSON-LD payload requested in the PR comments
    json_ld_payload = {
        "@context": "https://schema.org",
        "@type": "TechArticle",
        "name": "What is SUSE Rancher Prime? | SUSE Rancher Manager v2.16",
        "headline": "What is SUSE Rancher Prime?",
        "description": "Rancher adds significant value on top of Kubernetes...",
        "inLanguage": "en",
        "dateModified": "2026-06-16T00:00:00Z",
        "author": {
            "@type": "Organization",
            "name": "SUSE Product & Solution Documentation Team"
        },
        "mentions": [
            {
                "@type": "SoftwareApplication",
                "name": "SUSE Rancher Manager",
                "softwareVersion": "v2.16",
                "applicationCategory": "Cloud Infrastructure"
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

    result = extract_prebuilt_metadata(mock_deliverable, tmp_path)

    assert result["isGated"] is True
    assert result["category"] == "cloud-native"

    doc = result["docs"][0]
    assert doc["description"] == "Test description for admission controller."
    assert doc["title"] == "What is SUSE Rancher Prime?"
    assert doc["dateModified"] == "2026-06-16"
    assert doc["lang"] == "en-us"
    assert doc["default"] is True
    assert doc["format"]["html"] == "/admission-controller/latest/en/index.html"

    assert "SUSE Rancher Manager" in result["tasks"]
    assert result["products"][0]["name"] == "SUSE Security Admission Controller"
    assert result["products"][0]["versions"] == ["v2.16"]


def test_extract_prebuilt_metadata_missing_html(tmp_path: Path, mock_deliverable: Deliverable):
    """Test extraction gracefully handles missing HTML files."""
    result = extract_prebuilt_metadata(mock_deliverable, tmp_path)

    assert result["isGated"] is True
    assert result["category"] == "cloud-native"

    doc = result["docs"][0]
    # Should fall back to the XML description since HTML is missing
    assert doc["description"] == "Test description for admission controller."
    assert doc["format"]["html"] == "/admission-controller/latest/en/index.html"
    assert doc["title"] == "SUSE Security Admission Controller"
    assert "T" not in doc["dateModified"]
    assert result["tasks"] == []


def test_extract_prebuilt_metadata_no_json_ld(tmp_path: Path, mock_deliverable: Deliverable):
    """Test extraction gracefully handles HTML files missing the JSON-LD tag."""
    html_dir = tmp_path / "en-us" / "admission-controller" / "latest" / "en"
    html_dir.mkdir(parents=True)
    html_file = html_dir / "index.html"

    html_file.write_text("<html><head><title>Test</title></head></html>", encoding="utf-8")

    result = extract_prebuilt_metadata(mock_deliverable, tmp_path)

    doc = result["docs"][0]
    assert doc["title"] == "SUSE Security Admission Controller"
    assert "T" not in doc["dateModified"]
    assert result["tasks"] == []


def test_extract_prebuilt_metadata_malformed_json_ld(tmp_path: Path, mock_deliverable: Deliverable):
    """Test extraction gracefully handles malformed JSON-LD."""
    html_dir = tmp_path / "en-us" / "admission-controller" / "latest" / "en"
    html_dir.mkdir(parents=True)
    html_file = html_dir / "index.html"

    # Malformed JSON with a trailing comma
    malformed_json_payload = '''
    {
        "@context": "https://schema.org",
        "headline": "This JSON is broken",
    }
    '''

    html_file.write_text(
        f'''
        <html><head>
            <script type="application/ld+json">
            {malformed_json_payload}
            </script>
        </head><body>Test</body></html>
        ''',
        encoding="utf-8"
    )

    result = extract_prebuilt_metadata(mock_deliverable, tmp_path)

    assert result is not None
    doc = result["docs"][0]
    # Check that it safely fell back to XML values
    assert doc["title"] == "SUSE Security Admission Controller"
    assert result["tasks"] == []
