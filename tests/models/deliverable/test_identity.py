"""Identity and identifier tests for deliverables."""

from lxml import etree

from docbuild.models.deliverable import Deliverable


def test_product_id(first_deliverable: Deliverable) -> None:
    assert first_deliverable.xml.product_id == "sles"


def test_docset_fields(first_deliverable: Deliverable) -> None:
    assert first_deliverable.xml.docset_path == "15-SP6"
    assert first_deliverable.xml.docset_id == "sles.15-SP6"


def test_pdlang(first_deliverable: Deliverable) -> None:
    assert first_deliverable.pdlang == "sles/15-SP6/en-us"


def test_pdlangdc(first_deliverable: Deliverable) -> None:
    assert first_deliverable.pdlangdc == "sles/15-SP6/en-us:DC-SLES-administration"


def test_full_id(first_deliverable: Deliverable) -> None:
    assert (
        first_deliverable.full_id
        == "sles/15-SP6/maintenance_SLE15SP6/en-us:DC-SLES-administration"
    )


def test_lang_default(first_deliverable: Deliverable) -> None:
    assert first_deliverable.lang_is_default is True


def test_productname(first_deliverable: Deliverable) -> None:
    assert first_deliverable.xml.productname == "SUSE Linux Enterprise Server"


def test_acronym(first_deliverable: Deliverable) -> None:
    assert first_deliverable.xml.acronym == "SLES"


def test_dcfile(first_deliverable: Deliverable) -> None:
    assert first_deliverable.xml.dcfile == "DC-SLES-administration"


def test_dcfile_on_prebuilt(first_prebuilt_deliverable: Deliverable) -> None:
    assert first_prebuilt_deliverable.xml.dcfile is None
    expected_suffix = f":{first_prebuilt_deliverable.xml.deliverableid}"
    assert first_prebuilt_deliverable.full_id.endswith(expected_suffix)


def test_basefile(first_deliverable: Deliverable) -> None:
    assert first_deliverable.xml.basefile == "SLES-administration"


def test_locale_en_on_translated_deliverable(
    first_ref_deliverable: Deliverable,
) -> None:
    """Test that translated deliverables can resolve the English locale node."""
    locale_en = first_ref_deliverable.xml.locale_en
    assert locale_en is not None


def test_default_deliverables(first_ref_deliverable: Deliverable) -> None:
    """Test that translated deliverables yield docset default deliverables."""
    defaults = list(first_ref_deliverable.default_deliverables)
    assert len(defaults) > 0
    assert all(isinstance(d, Deliverable) for d in defaults)
    assert any(d.xml.dcfile == "DC-SLES-administration" for d in defaults)


def test_default_deliverables_without_default_locale() -> None:
    """Return an empty iterator when the docset has no default locale."""
    root = etree.fromstring(
        """
        <portal>
          <product xml:id="sles">
            <docset xml:id="sles.16" path="16.0">
              <resources>
                <locale lang="de-de">
                  <branch>main</branch>
                  <deliverable><dc file="DC-SLES-guide"/></deliverable>
                </locale>
              </resources>
            </docset>
          </product>
        </portal>
        """
    )
    node = root.find(".//deliverable")
    assert node is not None
    assert list(Deliverable(node).default_deliverables) == []


def test_dcfile_xref_cycle_returns_none() -> None:
    """Return None without recursion when an xref chain ends in a cycle."""
    root = etree.fromstring(
        """
        <portal xmlns:xml="http://www.w3.org/XML/1998/namespace">
          <product xml:id="sles">
            <docset xml:id="sles.16" path="16.0">
              <resources>
                <locale lang="en-us">
                  <deliverable xml:id="b" type="xref"><xref linkend="c"/></deliverable>
                  <deliverable xml:id="c" type="xref"><xref linkend="b"/></deliverable>
                </locale>
                <locale lang="de-de">
                  <deliverable xml:id="a" type="xref"><xref linkend="b"/></deliverable>
                </locale>
              </resources>
            </docset>
          </product>
        </portal>
        """
    )
    node = root.find(".//locale[@lang='de-de']/deliverable")
    assert node is not None
    assert Deliverable(node).xml.dcfile is None


def test_product_path(first_deliverable: Deliverable) -> None:
    assert first_deliverable.xml.product_path == "sles_path"
