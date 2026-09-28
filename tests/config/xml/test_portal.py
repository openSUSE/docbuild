"""Tests for the PortalConfig abstraction layer."""

from lxml import etree  # type: ignore
import pytest

from docbuild.config.xml.portal import PortalConfig


@pytest.fixture
def portal_tree() -> etree._ElementTree:
    """Provide a mock Portal XML tree for testing."""
    xml_content = b"""
    <portal schemaversion="7.0">
      <spotlight linkend="prod1" />
      <productfamilies>
        <item xml:id="fam1" rank="10" path="/fam">Family One</item>
      </productfamilies>
      <product xml:id="prod1" family="fam1" rank="100">
        <name>Product One</name>
        <descriptions>
          <desc lang="en-us"><title>Desc One</title></desc>
        </descriptions>
        <docset xml:id="doc1" path="1.0" lifecycle="supported">
          <version>1.0</version>
        </docset>
        <docset xml:id="doc2" path="2.0" lifecycle="unsupported">
          <version>2.0</version>
        </docset>
      </product>
      <product xml:id="sbp">
        <docset xml:id="sbp.1" path="sbp1">
          <version>SBP One</version>
        </docset>
      </product>
    </portal>
    """
    return etree.fromstring(xml_content)


def test_portal_config_initialization(portal_tree: etree._ElementTree) -> None:
    """Test that PortalConfig initializes correctly with an etree."""
    config = PortalConfig(tree=portal_tree)
    assert config.root is not None


def test_portal_config_spotlight(portal_tree: etree._ElementTree) -> None:
    """Test spotlight extraction and reference resolution."""
    config = PortalConfig(tree=portal_tree)
    spotlight = config.spotlight
    assert spotlight["spotlightLink"] == "/prod1/"
    assert spotlight["spotlightText"] == "Product One"


def test_portal_config_productfamilies(portal_tree: etree._ElementTree) -> None:
    """Test product family extraction."""
    config = PortalConfig(tree=portal_tree)
    families = config.productfamilies
    assert len(families) == 1
    assert families[0]["id"] == "fam1"
    assert families[0]["name"] == "Family One"
    assert families[0]["rank"] == "10"


def test_portal_config_categories(portal_tree: etree._ElementTree) -> None:
    """Test category extraction for specialized docsets."""
    config = PortalConfig(tree=portal_tree)
    categories = config.get_categories("sbp", "/sbp/")
    assert len(categories) == 1
    assert categories[0]["name"] == "SBP One"
    assert categories[0]["path"] == "/sbp/sbp1"


def test_portal_config_products(portal_tree: etree._ElementTree) -> None:
    """Test main product list extraction and mapping."""
    config = PortalConfig(tree=portal_tree)
    products = config.products

    assert len(products) == 1
    prod = products[0]
    assert prod["name"] == "Product One"
    assert prod["acronym"] == "prod1"
    # Proves family mapping works
    assert prod["product_family"] == "Family One"
    assert prod["rank"] == "100"

    assert len(prod["description"]) == 1
    assert prod["description"][0]["description"] == "Desc One"

    assert len(prod["supported"]) == 1
    assert prod["supported"][0]["path"] == "/prod1/1.0/"

    assert len(prod["unsupported"]) == 1
    assert prod["unsupported"][0]["path"] == "/prod1/2.0/"
