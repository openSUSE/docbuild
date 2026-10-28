from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from lxml import etree
import pytest

from docbuild.models.doctype import Doctype
from docbuild.tasks.translations import resolve_actual_translations


@pytest.mark.asyncio
async def test_resolve_actual_translations_success(tmp_path: Path) -> None:
    """Test that translation resolution correctly identifies existing DC files."""
    root = etree.Element("portal")
    tree = etree.ElementTree(root)
    doctype = Doctype.from_str("sles/15/en-us")

    # Mock a deliverable representing a German translation
    mock_d = MagicMock()
    mock_d.xml.is_dc = True
    mock_d.xml.is_xref = False
    mock_d.xml.lang = "de-de"
    mock_d.xml.dcfile = "DC-test-file"
    mock_d.xml.target_id = "test_target"

    mock_d.git.url = "https://git.test"
    mock_d.branch = "main"
    mock_d.subdir = ""

    with patch("docbuild.tasks.translations.get_deliverable_from_doctype", return_value=[mock_d]):
        with patch("docbuild.tasks.translations.ManagedGitRepo") as mock_repo_class:
            mock_repo_instance = mock_repo_class.return_value
            mock_repo_instance.clone_bare = AsyncMock()
            # Simulate the Git tree actually containing the translated DC file
            mock_repo_instance.ls_tree = AsyncMock(return_value=["DC-test-file"])

            result = await resolve_actual_translations(tree, doctype, tmp_path)

            assert "test_target" in result
            assert "de-de" in result["test_target"]
