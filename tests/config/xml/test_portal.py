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
    config = PortalConfig(source=portal_tree)
    assert config.root is not None


@pytest.mark.parametrize(
    "spotlight_xml, expected_link, expected_text",
    [
        # a) Product target
        ('<spotlight linkend="prod1" />', "/prod1/", "Product One"),
        # b) Docset target
        ('<spotlight linkend="doc1" />', "/prod1/1.0/", "Product One 1.0"),
        # c) Deliverable target
        ('<spotlight linkend="deliv1" />', "/prod1/1.0/", "Product One 1.0"),
        # d) Invalid/Unknown target
        ('<spotlight linkend="unknown_target" />', "/unknown_target/", ""),
    ]
)
def test_portal_config_spotlight_targets(spotlight_xml: str, expected_link: str, expected_text: str) -> None:
    """Test spotlight extraction and reference resolution for all target types."""
    # We must provide a fully structured product/docset so Deliverable() can resolve parents
    xml_content = f"""
    <portal schemaversion="7.0">
      {spotlight_xml}
      <product xml:id="prod1">
        <name>Product One</name>
        <docset xml:id="doc1" path="1.0">
          <version>1.0</version>
          <deliverables>
            <deliverable xml:id="deliv1" type="dc" format="html">
              <title>Deliv One</title>
            </deliverable>
          </deliverables>
        </docset>
      </product>
    </portal>
    """
    tree = etree.fromstring(xml_content.encode("utf-8"))
    config = PortalConfig(source=tree)
    spotlight = config.spotlight
    assert spotlight.get("spotlightLink") == expected_link
    assert spotlight.get("spotlightText") == expected_text


def test_portal_config_productfamilies(portal_tree: etree._ElementTree) -> None:
    """Test product family extraction."""
    config = PortalConfig(source=portal_tree)
    families = list(config.productfamilies)
    assert len(families) == 1
    assert families[0]["id"] == "fam1"
    assert families[0]["name"] == "Family One"
    assert families[0]["rank"] == "10"


def test_portal_config_categories(portal_tree: etree._ElementTree) -> None:
    """Test category extraction for specialized docsets."""
    config = PortalConfig(source=portal_tree)
    categories = list(config.get_categories("sbp"))
    assert len(categories) == 1
    assert categories[0]["name"] == "SBP One"
    assert categories[0]["path"] == "/sbp/sbp1/"


def test_portal_config_products(portal_tree: etree._ElementTree) -> None:
    """Test main product list extraction and mapping."""
    config = PortalConfig(source=portal_tree)
    products = list(config.products)

    assert len(products) == 1
    prod = products[0]
    assert prod["name"] == "Product One"
    assert prod["acronym"] == "prod1"
    assert prod["product_family"] == "Family One"
    assert prod["rank"] == "100"

    assert len(prod["description"]) == 1
    assert prod["description"][0]["description"] == "Desc One"

    assert len(prod["supported"]) == 1
    assert prod["supported"][0]["path"] == "/prod1/1.0/"

    assert len(prod["unsupported"]) == 1
    assert prod["unsupported"][0]["path"] == "/prod1/2.0/"
