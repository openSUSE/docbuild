from pathlib import Path
import tempfile

from lxml import etree
import pytest

from docbuild.config.xml.stitch import (
    create_stitchfile,
    load_check_functions,
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
            assert func.__name__.startswith('check_')



class TestCreateStitchfile:
    @pytest.mark.skip("TODO")
    def test_create_stitchfile_with_xml_files(self, tmp_path):
        """Test create_stitchfile with XML files in directory."""
        # This will cover lines 52-58
        with tempfile.TemporaryDirectory(dir=tmp_path) as tmpdir:
            config_dir = Path(tmpdir)

            # Create some XML files that match the default pattern [a-zA-Z0-9]*.xml
            xml1 = config_dir / 'config1.xml'
            xml1.write_text("""<?xml version="1.0"?>
<product product="test1">
    <name>Product 1</name>
</product>""")

            xml2 = config_dir / 'config2.xml'
            xml2.write_text("""<?xml version="1.0"?>
<product product="test2">
    <name>Product 2</name>
</product>""")

            # Create the stitch file
            result = create_stitchfile(config_dir)

            assert isinstance(result, etree._ElementTree)
            root = result.getroot()
            assert root.tag == 'docservconfig'

            # Should contain both XML files as children
            children = list(root)
            assert len(children) == 2
            assert all(child.tag == 'product' for child in children)
