"""Category lookup tests for deliverables."""

from lxml import etree

from docbuild.models.deliverable import Deliverable


def test_desc_empty(root_categories_node: etree._ElementTree) -> None:
    """Test desc() generator when no descriptions exist."""
    first_node = root_categories_node.xpath(
        "(/product | /portal/product)/docset/resources/locale[@lang='en-us']/deliverable"
    )[0]
    deliverable = Deliverable(first_node)
    assert len(list(deliverable.xml.desc())) == 0


def test_categories_from_product(root_categories_node: etree._ElementTree) -> None:
    first_node = root_categories_node.xpath(
        "(/product | /portal/product)/docset/resources/locale[@lang='en-us']/deliverable"
    )[0]
    deliverable = Deliverable(first_node)
    assert len(list(deliverable.xml.categories())) == 1


def test_categories_from_root(root_categories_node: etree._ElementTree) -> None:
    first_node = root_categories_node.xpath(
        "(/product | /portal/product)/docset/resources/locale[@lang='en-us']/deliverable"
    )[0]
    deliverable = Deliverable(first_node)
    assert len(list(deliverable.xml.categories_from_root())) == 1


def test_all_categories(root_categories_node: etree._ElementTree) -> None:
    first_node = root_categories_node.xpath(
        "(/product | /portal/product)/docset/resources/locale[@lang='en-us']/deliverable"
    )[0]
    deliverable = Deliverable(first_node)
    assert len(list(deliverable.xml.all_categories)) == 2
