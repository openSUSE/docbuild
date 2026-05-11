"""Tests for readable semantic XPath generation."""

from lxml import etree
import pytest

from docbuild.config.xml.semantic_xpath import (
    is_unique_among_same_tag_siblings,
    position_among_same_tag_siblings,
    semantic_xpath,
    xpath_literal,
)


def test_semantic_xpath_prefers_stable_attributes() -> None:
    """Use id/lang attributes when they uniquely identify nodes."""
    root = etree.fromstring(
        """
        <portal>
            <product id="sles">
                <docset id="sles.16.0">
                    <resources>
                        <locale lang="de-de"/>
                    </resources>
                </docset>
            </product>
        </portal>
        """,
        parser=None,
    )

    node = root.find(".//locale")
    assert node is not None

    result = semantic_xpath(node)

    expected = (
        "/portal/product[@id='sles']"
        "/docset[@id='sles.16.0']"
        "/resources[1]"
        "/locale[@lang='de-de']"
    )
    assert result == expected


def test_semantic_xpath_falls_back_to_position_for_ambiguous_siblings() -> None:
    """Fallback to positional predicates when attributes are ambiguous."""
    root = etree.fromstring(
        """
        <portal>
            <product id="sles">
                <docset id="sles.16.0">
                    <resources>
                        <locale lang="en-us"/>
                        <locale lang="en-us"/>
                    </resources>
                </docset>
            </product>
        </portal>
        """,
        parser=None,
    )

    second_locale = root.findall(".//locale")[1]
    result = semantic_xpath(second_locale)

    assert result.endswith("/locale[2]")


@pytest.mark.parametrize(
    "input_value,expected_output",
    [
        ("o'hara", '"o\'hara"'),
        ('he said "it\'s fine"', "concat('he said \"it', \"'\", 's fine\"')"),
    ],
)
def test_xpath_literal_escaping(input_value: str, expected_output: str) -> None:
    """XPath literals are properly escaped for various quote patterns."""
    assert xpath_literal(input_value) == expected_output


def test_is_unique_among_same_tag_siblings_for_root_node() -> None:
    """Root nodes are treated as unique because they have no parent."""
    root = etree.fromstring("<portal id=\"root\"/>", parser=None)

    assert is_unique_among_same_tag_siblings(root, "id", "root")


def test_position_among_same_tag_siblings_for_root_node() -> None:
    """Root nodes have no parent and therefore position 1."""
    root = etree.fromstring("<portal id=\"root\"/>", parser=None)

    assert position_among_same_tag_siblings(root) == 1


def test_is_unique_ignores_non_element_siblings() -> None:
    """Comments or processing instructions are ignored while checking uniqueness."""
    root = etree.fromstring(
        """
        <portal>
            <locale lang="en-us"/>
            <!-- comment node should be ignored -->
            <locale lang="de-de"/>
        </portal>
        """,
        parser=None,
    )

    locale = root.findall("./locale")[0]
    assert is_unique_among_same_tag_siblings(locale, "lang", "en-us")


@pytest.mark.parametrize(
    "element_name,attr_name,attr_values",
    [
        ("category", "lang", ("en-us", "de-de")),
        ("item", "id", ("f.linux", "f.cn")),
        ("desc", "lang", ("en-us", "de-de")),
    ],
)
def test_semantic_xpath_uses_preferred_attribute(
    element_name: str, attr_name: str, attr_values: tuple[str, str]
) -> None:
    """Elements use their preferred attribute as predicate."""
    root = etree.fromstring(
        f"""
        <portal>
            <wrapper>
                <{element_name} {attr_name}="{attr_values[0]}"/>
                <{element_name} {attr_name}="{attr_values[1]}"/>
            </wrapper>
        </portal>
        """,
        parser=None,
    )

    second_element = root.findall(f".//{element_name}")[1]
    result = semantic_xpath(second_element)

    assert result.endswith(f"/{element_name}[@{attr_name}='{attr_values[1]}']")


def test_semantic_xpath_uses_file_for_dc() -> None:
    """DC elements use file attribute as predicate."""
    root = etree.fromstring(
        """
        <portal>
            <docset>
                <dc file="DC-TEST-ONE"/>
                <dc file="DC-TEST-TWO"/>
            </docset>
        </portal>
        """,
        parser=None,
    )

    dc_two = root.findall(".//dc")[1]
    result = semantic_xpath(dc_two)

    assert result.endswith("/dc[@file='DC-TEST-TWO']")


@pytest.mark.parametrize(
    "attr_name,attr_value",
    [
        ("id", "cat.root"),
        ("linkend", "cat.root"),
    ],
)
def test_semantic_xpath_uses_language_attributes(
    attr_name: str, attr_value: str
) -> None:
    """Language elements use id or linkend attributes as predicates."""
    root = etree.fromstring(
        f"""
        <portal>
            <categories>
                <category lang="de-de">
                    <language {attr_name}="{attr_value}" title="Root"/>
                </category>
            </categories>
        </portal>
        """,
        parser=None,
    )

    language = root.find(".//language")
    result = semantic_xpath(language)

    assert f"/language[@{attr_name}='{attr_value}']" in result
