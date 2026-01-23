
from lxml import etree
import pytest

from docbuild.config.xml.stitch import (
    check_stitchfile,
    create_stitchfile,
    load_check_functions,
)


@pytest.fixture
def product_xml_string() -> str:
    """Return the raw XML string for a single product, without the root wrapper."""
    return """
        <product productid="fake" schemaversion="6.0">
            <name>Fake Doc</name>
            <acronym>fake</acronym>
            <category categoryid="container">
                <language lang="en-us" default="1" title="Containerization"/>
            </category>
            <desc default="1" lang="en-us">
              <title>A fake title</title>
              <p>This is a fake description.</p>
            </desc>
            <docset setid="1" lifecycle="supported">
                <version>1.0</version>
                <overridedesc treatment="append">
                    <desc default="1" lang="en-us">
                        <p>Doc fake addition</p>
                    </desc>
                </overridedesc>
                <builddocs>
                    <git remote="https://github.com/SUSE/doc-fakedoc.git"/>
                    <language lang="en-us" default="1">
                        <deliverable>
                            <dc>DC-GNOME-getting-started</dc>
                            <format html="1" pdf="1" single-html="0"/>
                        </deliverable>
                    </language>
                </builddocs>
                <internal>
                    <ref product="fake" docset="1" dc="DC-GNOME-getting-started" />
               </internal>
            </docset>
        </product>
"""


@pytest.fixture
def xmlnode(product_xml_string: str) -> etree._Element:
    """Return a full, parsed <docservconfig> element tree for direct checks."""
    return etree.fromstring(
        f"<docservconfig>{product_xml_string}</docservconfig>",
        parser=None,
    )


class TestLoadCheckFunctions:
    def test_load_check_functions_returns_list(self):
        """Test that load_check_functions returns a list of callable functions."""
        # This will cover lines 15-17
        functions = load_check_functions()

        assert isinstance(functions, list)
        # Should return functions that start with "check_"
        for func in functions:
            assert callable(func)
            assert func.__name__.startswith("check_")


class TestStitchfile:
    async def test_create_stitchfile_with_xml_files(self, tmp_path):
        """Test create_stitchfile with XML files in directory."""
        # This will cover lines 52-58
        # Create some XML files
        xml1 = tmp_path / "config1.xml"
        xml1.write_text("""<product productid="test1">
<name>Product 1</name>
</product>""")

        xml2 = tmp_path / "config2.xml"
        xml2.write_text("""<product productid="test2">
<name>Product 2</name>
</product>""")

        # Create the stitch file, disable ref check for this basic test
        result = await create_stitchfile([xml1, xml2], with_ref_check=False)

        assert isinstance(result, etree._ElementTree)
        root = result.getroot()
        assert root.tag == "docservconfig"

        # Should contain both XML files as children
        children = list(root)
        assert len(children) == 2
        assert all(child.tag == "product" for child in children)

    def test_check_stitchfile_valid_refs(self, xmlnode):
        """Test check_stitchfile with valid references."""
        result = check_stitchfile(xmlnode)
        assert result

    def test_check_stitchfile_invalid_product_ref(self, xmlnode):
        """Test check_stitchfile with an invalid product reference."""
        internal_node = xmlnode.find(".//internal")
        # Add a ref to a product that does not exist
        etree.SubElement(
            internal_node,
            "ref",
            attrib={
                "product": "invalid-product",
                "docset": "unknown",
                "dc": "DC-unknown",
            },
        )
        result = check_stitchfile(xmlnode)
        assert not result

    async def test_create_stitchfile_with_ref_check_failure(self, tmp_path):
        """Test create_stitchfile raises ValueError on unresolved references."""
        invalid_xml_content = """
<product productid="p1">
  <docset setid="d1">
    <internal>
      <ref product="p2" /> <!-- p2 does not exist -->
    </internal>
  </docset>
</product>
"""
        xml_file = tmp_path / "invalid.xml"
        xml_file.write_text(invalid_xml_content)

        with pytest.raises(
            ValueError, match="Unresolved references found in stitch file"
        ):
            await create_stitchfile([xml_file], with_ref_check=True)

        # Check that the specific error was logged from check_stitchfile
        # assert (
        #     "Failed reference from 'p1/d1' to p2: Referenced product does not exist."
        #     in caplog.text
        # )

    async def test_create_stitchfile_without_ref_check(self, tmp_path):
        """Test create_stitchfile succeeds with unresolved refs if check is disabled."""
        invalid_xml_content = """
<product productid="p1">
  <docset setid="d1">
    <internal>
      <ref product="p2" /> <!-- p2 does not exist -->
    </internal>
  </docset>
</product>
"""
        xml_file = tmp_path / "invalid.xml"
        xml_file.write_text(invalid_xml_content)

        # This should not raise an error
        result = await create_stitchfile([xml_file], with_ref_check=False)
        assert isinstance(result, etree._ElementTree)
        root = result.getroot()
        assert root.tag == "docservconfig"
        assert len(root.findall("product")) == 1

    async def test_create_stitchfile_with_valid_refs_does_not_raise(
        self, product_xml_string, tmp_path
    ):
        """Test create_stitchfile succeeds when references are valid."""
        xml_file = tmp_path / "valid.xml"
        xml_file.write_text(product_xml_string)

        # This should not raise an error
        result = await create_stitchfile([xml_file], with_ref_check=True)
        assert isinstance(result, etree._ElementTree)
