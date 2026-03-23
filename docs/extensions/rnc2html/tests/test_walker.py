"""
Tests for RNC schema walker logic.
"""
import sys
from pathlib import Path
from lxml import etree  # type: ignore[import-untyped]
import pytest

# Add extension source to path
# We are in docs/extensions/rnc2html/tests
EXTENSION_ROOT = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(EXTENSION_ROOT))

# Import after path setup
try:
    from rnc2html.walker import SchemaWalker
except ImportError as e:
    # If run standalone, retry assuming relative path issue or module load
    # But sys.path logic above should fix it
    print(f"Could not import rnc2html.walker. Check PYTHONPATH setup. Error: {e}")
    raise e

RNG_SAMPLE = """
<grammar xmlns="http://relaxng.org/ns/structure/1.0"
         xmlns:db="http://docbook.org/ns/docbook"
         xmlns:a="http://relaxng.org/ns/compatibility/annotations/1.0">
  <start>
    <ref name="root"/>
  </start>

  <define name="root">
    <element name="book">
      <db:refpurpose>A book element.</db:refpurpose>
      <attribute name="id">
        <a:documentation>Unique identifier.</a:documentation>
      </attribute>
      <optional>
        <attribute name="lang"/>
      </optional>
      <ref name="chapter"/>
    </element>
  </define>

  <define name="chapter">
    <element name="chapter">
       <db:refpurpose>A chapter.</db:refpurpose>
       <text/>
    </element>
  </define>
</grammar>
"""


def test_walker_basic() -> None:
    """Test basic schema traversal and extraction."""
    tree = etree.fromstring(RNG_SAMPLE.encode("utf-8")).getroottree()
    walker = SchemaWalker(tree)
    elements = walker.walk()

    assert len(elements) == 2

    # Verify Book element
    book = next((e for e in elements if e.name == "book"), None)
    assert book is not None
    assert book.description == "A book element."
    assert len(book.attributes) == 2

    id_attr = next((a for a in book.attributes if a.name == "id"), None)
    assert id_attr is not None
    assert id_attr.required is True
    assert id_attr.description == "Unique identifier."

    lang_attr = next((a for a in book.attributes if a.name == "lang"), None)
    assert lang_attr is not None
    assert lang_attr.required is False
    assert lang_attr.description is None  # No doc provided

# Verify Children references
    # The walker appends "Ref:name" for pattern references
    assert ("Ref:chapter", "1") in book.children
    assert book.content_model is not None


def test_missing_refpurpose() -> None:
    """Test fallback to a:documentation or None."""
    rng = """
    <grammar xmlns="http://relaxng.org/ns/structure/1.0"
             xmlns:a="http://relaxng.org/ns/compatibility/annotations/1.0">
      <start>
        <element name="foo">
          <empty/>
        </element>
      </start>
    </grammar>
    """
    tree = etree.fromstring(rng.encode("utf-8")).getroottree()
    walker = SchemaWalker(tree)
    elements = walker.walk()

    foo = elements[0]
    assert foo.name == "foo"
    assert foo.description is None


def test_content_model_complex() -> None:
    """Test content model string generation for complex structures."""
    rng = """
    <grammar xmlns="http://relaxng.org/ns/structure/1.0">
      <start><ref name="root"/></start>
      <define name="root">
        <element name="root">
          <oneOrMore>
            <choice>
              <element name="foo"><empty/></element>
              <element name="bar"><empty/></element>
            </choice>
          </oneOrMore>
          <optional>
             <element name="baz"><text/></element>
          </optional>
        </element>
      </define>
    </grammar>
    """
    tree = etree.fromstring(rng.encode("utf-8")).getroottree()
    walker = SchemaWalker(tree)
    elements = walker.walk()

    root = elements[0]
    # Expected: ((<foo> | <bar>)+ , (<baz>)?) or similar logic depending on implementation detail

    print(f"DEBUG: {root.content_model}")
    assert root.content_model is not None
    assert "<foo>" in root.content_model
    assert "<bar>" in root.content_model
    assert "|" in root.content_model
    assert "+" in root.content_model
    assert "?" in root.content_model

if __name__ == "__main__":
    test_walker_basic()
    test_missing_refpurpose()
    test_content_model_complex()
    print("All tests passed!")

def test_walker_with_comments() -> None:
    """Test schema with comments inside definitions."""
    rng = """
    <grammar xmlns="http://relaxng.org/ns/structure/1.0">
      <start>
        <!-- This is a start comment -->
        <ref name="root"/>
      </start>
      <!-- Defines comment -->
      <define name="root">
        <!-- Element comment -->
        <element name="doc">
           <text/>
        </element>
      </define>
    </grammar>
    """
    tree = etree.fromstring(rng.encode("utf-8")).getroottree()
    walker = SchemaWalker(tree)
    elements = walker.walk()
    assert len(elements) == 1
    assert elements[0].name == "doc"
