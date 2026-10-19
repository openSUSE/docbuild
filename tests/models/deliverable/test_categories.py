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


def test_category_title_xinclude_and_localized() -> None:
    """Test category_title and category_titles resolve localized and multi-ID categories."""
    xml_content = """
    <portal>
        <categories>
            <category lang="en-us">
                <language xml:id="cat.about">
                    <title>About</title>
                </language>
                <language xml:id="cat.deployment">
                    <title>Deployment</title>
                </language>
            </category>
            <category lang="de-de">
                <language linkend="cat.about">
                    <title>Über</title>
                </language>
                <language linkend="cat.deployment">
                    <title>Bereitstellung</title>
                </language>
            </category>
        </categories>
        <product xml:id="sles">
            <docset path="16.0">
                <resources>
                    <locale lang="en-us">
                        <deliverable xml:id="d-en" category="cat.about cat.deployment">
                            <dc file="DC-test"/>
                        </deliverable>
                    </locale>
                    <locale lang="de-de">
                        <deliverable xml:id="d-de" type="xref">
                            <xref linkend="d-en"/>
                        </deliverable>
                    </locale>
                </resources>
            </docset>
        </product>
    </portal>
    """
    root = etree.fromstring(xml_content)
    d_en = Deliverable(root.xpath("//deliverable[@xml:id='d-en']")[0])
    d_de = Deliverable(root.xpath("//deliverable[@xml:id='d-de']")[0])

    assert d_en.xml.category_titles == ["About", "Deployment"]
    assert d_en.xml.category_title == "About, Deployment"
    assert d_de.xml.category_titles == ["Über", "Bereitstellung"]
    assert d_de.xml.category_title == "Über, Bereitstellung"
