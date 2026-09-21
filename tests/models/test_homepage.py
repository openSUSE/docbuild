"""Tests for the Homepage JSON generation model."""

import json
from pathlib import Path

from lxml import etree  # type: ignore
import pytest

from docbuild.models.homepage import Homepage, ProductItem


@pytest.fixture
def sample_portal_xml() -> etree._ElementTree:
    """Provide a mock Portal XML configuration for testing."""
    xml_content = b"""
    <portal schemaversion="7.0">
      <!-- Test empty spotlight tag auto-generation -->
      <spotlight linkend="app-1" />

      <productfamilies>
        <!-- Test missing rank (should fall back to enumerate count '1') -->
        <item xml:id="f.linux" path="/linux">Linux</item>
      </productfamilies>

      <product xml:id="sbp">
        <docset xml:id="sbp.cloud" path="/cloud">
          <version>Cloud Computing</version>
        </docset>
      </product>

      <product xml:id="trd">
        <docset xml:id="trd.amd" path="amd/">
          <version>AMD</version>
        </docset>
      </product>

      <product xml:id="smart">
        <docset xml:id="smart.container" path="container/">
          <!-- Test Smart Docs prefix stripping -->
          <version>Smart Docs: Containerization</version>
        </docset>
      </product>

      <!-- Test mapping family ID 'f.linux' back to 'Linux' -->
      <product xml:id="app-building" family="f.linux" rank="04150">
        <name>Appliance Building</name>
        <descriptions>
          <desc lang="en-us">
            <!-- Test extracting ONLY the title -->
            <title>A short description with bold text.</title>
            <p>Ignore this paragraph.</p>
          </desc>
        </descriptions>
        <docset xml:id="app-1" path="1.0" lifecycle="supported">
          <version>App Builder 1.0</version>
          <!-- Nested deliverable version to prove we don't accidentally grab it (the Keg bug) -->
          <deliverable><version>Keg Image Generator</version></deliverable>
        </docset>
        <docset xml:id="app-2" path="2.0">
          <version>App Builder 2.0</version>
        </docset>
        <docset xml:id="app-0.9" path="0.9" lifecycle="unsupported">
          <version>App Builder 0.9</version>
        </docset>
      </product>
    </portal>
    """
    return etree.fromstring(xml_content)


def test_homepage_from_portal_extraction(sample_portal_xml: etree._ElementTree):
    """Test that Homepage model extracts data perfectly from Portal XML."""
    hp = Homepage.from_portal(sample_portal_xml)

    # 1. Test rank enumeration
    assert len(hp.product_families) == 1
    assert hp.product_families[0].name == "Linux"
    assert hp.product_families[0].rank == "1"

    # 2. Test specialized categories
    assert len(hp.sbp_category_list) == 1
    assert hp.sbp_category_list[0].path == "/sbp/cloud"

    assert len(hp.trd_partner_list) == 1
    assert hp.trd_partner_list[0].path == "/trd/amd/"

    assert len(hp.smart_doc_category_list) == 1
    assert hp.smart_doc_category_list[0].name == "Containerization"

    # 3. Test standard product parsing
    assert len(hp.products_list) == 1
    prod = hp.products_list[0]

    assert prod.name == "Appliance Building"
    assert prod.acronym == "app-building"
    # Proves family 'f.linux' was mapped perfectly back to 'Linux'
    assert prod.product_family == "Linux"

    # Proves only <title> was extracted and structured as a dict
    assert len(prod.description) == 1
    assert prod.description[0].lang == "en-us"
    assert prod.description[0].default is True
    assert prod.description[0].description == "A short description with bold text."

    # Proves we got the correct docset version, avoiding the nested 'Keg' deliverable
    assert len(prod.supported) == 2
    assert prod.supported[0].name == "App Builder 1.0"
    assert prod.supported[0].path == "/app-building/1.0/"
    assert prod.supported[1].name == "App Builder 2.0"
    assert prod.supported[1].path == "/app-building/2.0/"

    assert len(prod.unsupported) == 1
    assert prod.unsupported[0].name == "App Builder 0.9"
    assert prod.unsupported[0].path == "/app-building/0.9/"

    # 4. Test auto-generating empty spotlight using Deliverable methods
    assert hp.spotlight_link == "/app-building/1.0/"
    assert hp.spotlight_text == "Appliance Building App Builder 1.0"


def test_homepage_save_serializes_correctly(tmp_path: Path):
    """Test that saving the model generates correct JSON, specifically the 'acronym' alias."""
    hp = Homepage(
        products_list=[
            ProductItem(
                name="Test Prod",
                acronym="test-acronym",
                product_family="Test Family",
                rank="1"
            )
        ]
    )

    output_file = tmp_path / "homepage.json"
    hp.save(output_file)

    data = json.loads(output_file.read_text())

    assert "productsList" in data
    assert "acronym" in data["productsList"][0]
    assert data["productsList"][0]["acronym"] == "test-acronym"
