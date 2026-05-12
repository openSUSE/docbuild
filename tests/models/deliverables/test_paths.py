"""Deliverable path generation tests."""

import pytest

from docbuild.models.deliverable import Deliverable
from docbuild.models.metadata import Metadata


def test_relpath(first_deliverable: Deliverable) -> None:
    assert first_deliverable.paths.relpath == "en-us/sles/15-SP6"


def test_zip_path(first_deliverable: Deliverable) -> None:
    assert first_deliverable.paths.zip_path == "en-us/sles/15-SP6/sles-15-SP6-en-us.zip"


def test_html_path(first_deliverable: Deliverable) -> None:
    assert first_deliverable.paths.html_path == "/sles/15-SP6/html/SLES-administration/"


def test_singlehtml_path(first_deliverable: Deliverable) -> None:
    assert (
        first_deliverable.paths.singlehtml_path
        == "/sles/15-SP6/single-html/SLES-administration/"
    )


def test_pdf_path(first_deliverable: Deliverable) -> None:
    assert first_deliverable.paths.pdf_path == "/sles/15-SP6/pdf/SLES-administration_en.pdf"


def test_pdf_path_non_default_lang(first_de_deliverable: Deliverable) -> None:
    assert (
        first_de_deliverable.paths.pdf_path
        == "/de-de/sles/15-SP6/pdf/SLES-administration_de.pdf"
    )


def test_html_path_with_meta_rootid(first_de_deliverable: Deliverable) -> None:
    first_de_deliverable.meta = Metadata(rootid="foo")
    assert first_de_deliverable.paths.html_path == "/de-de/sles/15-SP6/html/foo/"


def test_base_format_path_missing_dcfile_raises(
    first_prebuilt_deliverable: Deliverable,
) -> None:
    """Test that a ValueError is raised when trying to generate a path without a DC file."""
    with pytest.raises(ValueError, match="No DC filename found for path generation"):
        _ = first_prebuilt_deliverable.paths.base_format_path("html")


def test_base_format_path_with_meta_missing_rootid(
    first_deliverable: Deliverable, meta_without_rootid: Metadata
) -> None:
    """Test path fallback when meta is present but missing a rootid."""
    first_deliverable.meta = meta_without_rootid
    assert first_deliverable.paths.html_path == "/sles/15-SP6/html/SLES-administration/"


def test_pdf_path_missing_dcfile_raises(
    first_prebuilt_deliverable: Deliverable,
) -> None:
    """Test that a ValueError is raised when trying to generate a PDF path without a DC file."""
    with pytest.raises(ValueError, match="No DC filename found for PDF path generation"):
        _ = first_prebuilt_deliverable.paths.pdf_path


def test_paths_repr(
    first_deliverable: Deliverable, meta_without_rootid: Metadata
) -> None:
    """Test the string representation of DeliverablePaths."""
    first_deliverable.meta = meta_without_rootid
    representation = repr(first_deliverable.paths)
    assert representation.startswith("DeliverablePaths(xml=(")
    assert "meta=" in representation
