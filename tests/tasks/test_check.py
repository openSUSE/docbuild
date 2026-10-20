from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from docbuild.models.doctype import Doctype
from docbuild.tasks import check
from docbuild.tasks.check import check_repository_files


@pytest.fixture
def mock_deliverable():
    mock_deli = MagicMock()
    mock_deli.git = MagicMock()
    mock_deli.git.url = "gh://mock/repo"
    mock_deli.branch = "main"
    mock_deli.subdir = "."
    mock_deli.xml.dcfile = "README.md"
    mock_deli.xml.is_xref = False
    mock_deli.xml.is_prebuilt = False
    mock_deli.lang_is_default = True
    return mock_deli


@pytest.mark.asyncio
@patch.object(check, "parse_portal_config", new_callable=AsyncMock)
@patch.object(check, "get_deliverable_from_doctype")
@patch.object(check, "ManagedGitRepo")
async def test_check_repository_files_all_found(
    mock_repo_class, mock_get_deli, mock_parse_portal_config, tmp_path, mock_deliverable
):
    """Test full process when all files exist in the repo."""
    mock_parse_portal_config.return_value = MagicMock()
    mock_get_deli.return_value = [mock_deliverable]

    mock_repo = AsyncMock()
    mock_repo.clone_bare.return_value = True
    mock_repo.ls_tree.return_value = ["README.md"]
    mock_repo_class.return_value = mock_repo

    main_portal_config = tmp_path / "config.xml"
    main_portal_config.write_text("<xml/>")
    repo_root = tmp_path / "repos"

    result = await check_repository_files(main_portal_config, repo_root, doctypes=None)
    assert any(r.status == "found" for files in result.values() for r in files)


@pytest.mark.asyncio
@patch.object(check, "parse_portal_config", new_callable=AsyncMock)
@patch.object(check, "get_deliverable_from_doctype")
@patch.object(check, "ManagedGitRepo")
async def test_check_repository_files_missing(
    mock_repo_class, mock_get_deli, mock_parse_portal_config, tmp_path, mock_deliverable
):
    """Test full process when a file is missing in the repo."""
    mock_parse_portal_config.return_value = MagicMock()
    mock_get_deli.return_value = [mock_deliverable]

    mock_repo = AsyncMock()
    mock_repo.clone_bare.return_value = True
    mock_repo.ls_tree.return_value = ["LICENSE"]  # README.md is missing
    mock_repo_class.return_value = mock_repo

    main_portal_config = tmp_path / "config.xml"
    main_portal_config.write_text("<xml/>")
    repo_root = tmp_path / "repos"

    result = await check_repository_files(main_portal_config, repo_root, doctypes=None)
    assert any(r.status == "error" for files in result.values() for r in files)


@pytest.mark.asyncio
@patch.object(check, "parse_portal_config", new_callable=AsyncMock)
@patch.object(check, "get_deliverable_from_doctype")
@patch.object(check, "ManagedGitRepo")
async def test_process_git_failure(
    mock_repo_class, mock_get_deli, mock_parse_portal_config, tmp_path, mock_deliverable
):
    """Test coverage for the branch where Git cloning/fetching fails."""
    mock_parse_portal_config.return_value = MagicMock()
    mock_get_deli.return_value = [mock_deliverable]

    mock_repo = AsyncMock()
    mock_repo.clone_bare.return_value = False  # Simulate failure
    mock_repo_class.return_value = mock_repo

    main_portal_config = tmp_path / "config.xml"
    main_portal_config.write_text("<xml/>")
    repo_root = tmp_path / "repos"

    result = await check_repository_files(main_portal_config, repo_root, doctypes=None)
    assert any(r.status == "error" for files in result.values() for r in files)


@pytest.mark.asyncio
@patch.object(check, "parse_portal_config", new_callable=AsyncMock)
@patch.object(check, "get_deliverable_from_doctype")
@patch.object(check, "ManagedGitRepo")
async def test_check_repository_files_skips_deliverables_without_git(
    mock_repo_class, mock_get_deli, mock_parse_portal_config, tmp_path
):
    """Deliverables without a Git repository must not crash the check (#635)."""
    deli = MagicMock()
    deli.git = None
    deli.pdlangdc = "sles/16.0/en-us:DC-fake"
    deli.xml.dcfile = "DC-fake"
    deli.xml.is_prebuilt = False
    deli.xml.is_xref = False

    mock_parse_portal_config.return_value = MagicMock()
    mock_get_deli.return_value = [deli]

    main_portal_config = tmp_path / "config.xml"
    main_portal_config.write_text("<xml/>")
    repo_root = tmp_path / "repos"

    result = await check_repository_files(main_portal_config, repo_root, doctypes=None)
    assert any(r.status == "skipped" for files in result.values() for r in files)


@pytest.mark.asyncio
@patch.object(check, "parse_portal_config", new_callable=AsyncMock)
@patch.object(check, "get_deliverable_from_doctype")
async def test_process_no_deliverables_found(mock_get_deli, mock_parse_portal_config, tmp_path):
    """Test path where stitch tree returns no deliverables."""
    mock_parse_portal_config.return_value = MagicMock()
    mock_get_deli.return_value = []  # No deliverables

    main_portal_config = tmp_path / "config.xml"
    main_portal_config.write_text("<xml/>")
    repo_root = tmp_path / "repos"

    result = await check_repository_files(main_portal_config, repo_root, doctypes=None)
    assert not any(result.values())


@pytest.mark.asyncio
@patch.object(check, "parse_portal_config", new_callable=AsyncMock)
async def test_process_no_xml_files(mock_parse_portal_config, tmp_path):
    """Verify behavior when the main portal config is missing."""
    main_portal_config = tmp_path / "missing.xml"
    repo_root = tmp_path / "repos"

    result = await check_repository_files(main_portal_config, repo_root, doctypes=None)
    assert not any(result.values())


@pytest.mark.asyncio
@patch.object(check, "parse_portal_config", new_callable=AsyncMock)
@patch.object(check, "get_deliverable_from_doctype")
@patch.object(check, "ManagedGitRepo")
async def test_check_repository_files_with_explicit_doctypes(
    mock_repo_class, mock_get_deli, mock_parse_portal_config, tmp_path, mock_deliverable
):
    """Test coverage for providing explicit doctypes instead of defaulting."""
    mock_parse_portal_config.return_value = MagicMock()
    mock_get_deli.return_value = [mock_deliverable]

    mock_repo = AsyncMock()
    mock_repo.clone_bare.return_value = True
    mock_repo.ls_tree.return_value = ["README.md"]
    mock_repo_class.return_value = mock_repo

    main_portal_config = tmp_path / "config.xml"
    main_portal_config.write_text("<xml/>")

    explicit_doctypes = [Doctype.from_str("sles/16.0/en-us")]

    result = await check_repository_files(
        main_portal_config, tmp_path / "repos", doctypes=explicit_doctypes
    )
    assert any(r.status == "found" for files in result.values() for r in files)
