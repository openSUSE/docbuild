"""Identity and identifier tests for deliverables."""

from docbuild.models.deliverable import Deliverable


def test_product_id(first_deliverable: Deliverable) -> None:
    assert first_deliverable.xml.productid == "sles"


def test_docset_fields(first_deliverable: Deliverable) -> None:
    assert first_deliverable.xml.docsetid == "15-SP6"
    assert first_deliverable.xml.docsetrealid == "sles.15-SP6"


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
    assert first_prebuilt_deliverable.full_id.endswith(":")  # No DC file suffix


def test_basefile(first_deliverable: Deliverable) -> None:
    assert first_deliverable.xml.basefile == "SLES-administration"


def test_locale_en_on_translated_deliverable(first_ref_deliverable: Deliverable) -> None:
    """Test that translated deliverables can resolve the English locale node."""
    locale_en = first_ref_deliverable.xml.locale_en
    assert locale_en is not None
    assert locale_en.get("lang") == "en-us"
