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
      <productfamilies>
        <productfamily name="Linux" rank="1" path="/linux"/>
      </productfamilies>
      <product id="sbp">
        <docset path="/cloud">
          <version>Cloud Computing</version>
        </docset>
      </product>
      <product id="trd">
        <docset path="amd/">
          <version>AMD</version>
        </docset>
      </product>
      <product id="smart">
        <docset path="container/">
          <version>Containerization</version>
        </docset>
      </product>
      <product id="app-building">
        <name>Appliance Building</name>
        <productfamily>Linux</productfamily>
        <rank>04150</rank>
        <description>
          <desc lang="en-us">
            <p>A short description with <b>bold</b> text.</p>
          </desc>
        </description>
        <docset id="app-1" lifecycle="supported">
          <name>App Builder 1.0</name>
        </docset>
        <docset id="app-2">
          <version>App Builder 2.0</version>
        </docset>
        <docset id="app-0.9" lifecycle="unsupported">
          <name>App Builder 0.9</name>
        </docset>
      </product>
      <spotlight linkend="/spotlight-link">
        <p>Check out the <i>newest</i> release!</p>
      </spotlight>
    </portal>
    """
    return etree.fromstring(xml_content)


def test_homepage_from_portal_extraction(sample_portal_xml: etree._ElementTree):
    """Test that Homepage model extracts data perfectly from Portal XML."""
    hp = Homepage.from_portal(sample_portal_xml)

    assert len(hp.product_families) == 1
    assert hp.product_families[0].name == "Linux"

    assert len(hp.sbp_category_list) == 1
    assert hp.sbp_category_list[0].path == "/sbp/cloud"

    assert len(hp.trd_partner_list) == 1
    assert hp.trd_partner_list[0].path == "/trd/amd/"

    assert len(hp.products_list) == 1
    prod = hp.products_list[0]
    assert prod.name == "Appliance Building"
    assert prod.acronym == "app-building"
    assert prod.product_family == "Linux"
    assert prod.description == ["A short description with bold text."]

    assert prod.supported == ["App Builder 1.0", "App Builder 2.0"]
    assert prod.unsupported == ["App Builder 0.9"]

    assert hp.spotlight_text == "Check out the newest release!"


def test_homepage_save_serializes_correctly(tmp_path: Path):
    """Test that saving the model generates correct JSON, specifically the 'acronymn' alias."""
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
    assert "acronymn" in data["productsList"][0]
    assert data["productsList"][0]["acronymn"] == "test-acronym"
