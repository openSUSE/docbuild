from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from docbuild.cli.cmd_check import process
from docbuild.cli.cmd_check.process import process_check_files


@pytest.fixture
def mock_deliverable():
    """Create a mock Deliverable object with required attributes."""
    deli = MagicMock()
    deli.productid = "sles"
    deli.docsetid = "16.0"
    deli.lang = "en-us"
    deli.dcfile = "README.md"
    deli.branch = "main"
    deli.git.url = "https://github.com/org/repo.git"
    deli.git.surl = "gh://org/repo"
    return deli

@patch.object(process, "create_stitchfile", new_callable=AsyncMock)
@patch.object(process, "get_deliverable_from_doctype")
@patch.object(process, "ManagedGitRepo")
async def test_process_check_files_all_found(
    mock_repo_class, mock_get_deli, mock_stitch, tmp_path, mock_deliverable
):
    """Test full process when all files exist in the repo."""
    # 1. Setup mocks
    mock_stitch.return_value = MagicMock()
    mock_get_deli.return_value = [mock_deliverable]

    mock_repo = AsyncMock()
    mock_repo.clone_bare.return_value = True
    mock_repo.ls_tree.return_value = ["README.md"]
    mock_repo_class.return_value = mock_repo

    # 2. Setup Context
    ctx = MagicMock()
    config_dir = tmp_path / "config.d"
    config_dir.mkdir()
    (config_dir / "test.xml").write_text("<xml/>")
    ctx.envconfig.paths.config_dir = config_dir
    ctx.envconfig.paths.repo_dir = tmp_path / "repos"

    # 3. Execute
    result = await process_check_files(ctx, doctypes=None)

    # 4. Assertions
    assert result == []
    mock_repo.clone_bare.assert_called_once()
    mock_repo.ls_tree.assert_called_with("main")

@patch.object(process, "create_stitchfile", new_callable=AsyncMock)
@patch.object(process, "get_deliverable_from_doctype")
@patch.object(process, "ManagedGitRepo")
async def test_process_check_files_missing(
    mock_repo_class, mock_get_deli, mock_stitch, tmp_path, mock_deliverable
):
    """Test full process when a file is missing in the repo."""
    mock_stitch.return_value = MagicMock()
    mock_get_deli.return_value = [mock_deliverable]

    mock_repo = AsyncMock()
    mock_repo.clone_bare.return_value = True
    mock_repo.ls_tree.return_value = ["LICENSE"] # README.md is missing
    mock_repo_class.return_value = mock_repo

    ctx = MagicMock()
    config_dir = tmp_path / "config.d"
    config_dir.mkdir()
    (config_dir / "test.xml").write_text("<xml/>")
    ctx.envconfig.paths.config_dir = config_dir
    ctx.envconfig.paths.repo_dir = tmp_path / "repos"

    result = await process_check_files(ctx, doctypes=None)

    # Check for the new formatted string output
    expected_error = "[gh://org/repo] sles/16.0/en-us:README.md"
    assert expected_error in result

@patch.object(process, "create_stitchfile", new_callable=AsyncMock)
@patch.object(process, "get_deliverable_from_doctype")
@patch.object(process, "ManagedGitRepo")
async def test_process_git_failure(
    mock_repo_class, mock_get_deli, mock_stitch, tmp_path, mock_deliverable
):
    """Test coverage for the branch where Git cloning/fetching fails."""
    mock_stitch.return_value = MagicMock()
    mock_get_deli.return_value = [mock_deliverable]

    mock_repo = AsyncMock()
    mock_repo.clone_bare.return_value = False # Simulate failure
    mock_repo_class.return_value = mock_repo

    ctx = MagicMock()
    config_dir = tmp_path / "config.d"
    config_dir.mkdir()
    (config_dir / "test.xml").write_text("<xml/>")
    ctx.envconfig.paths.config_dir = config_dir
    ctx.envconfig.paths.repo_dir = tmp_path / "repos"

    result = await process_check_files(ctx, doctypes=None)

    expected_error = "[gh://org/repo] sles/16.0/en-us:README.md"
    assert expected_error in result

@patch.object(process, "create_stitchfile", new_callable=AsyncMock)
@patch.object(process, "get_deliverable_from_doctype")
async def test_process_no_deliverables_found(mock_get_deli, mock_stitch, tmp_path):
    """Test path where stitch tree returns no deliverables."""
    mock_stitch.return_value = MagicMock()
    mock_get_deli.return_value = [] # No deliverables

    ctx = MagicMock()
    config_dir = tmp_path / "config.d"
    config_dir.mkdir()
    (config_dir / "test.xml").write_text("<xml/>")
    ctx.envconfig.paths.config_dir = config_dir

    result = await process_check_files(ctx, doctypes=None)
    assert result == []

@patch.object(process, "create_stitchfile", new_callable=AsyncMock)
async def test_process_no_xml_files(mock_stitch, tmp_path):
    """Verify behavior when no XML files are present at all."""
    ctx = MagicMock()
    config_dir = tmp_path / "empty"
    config_dir.mkdir()
    ctx.envconfig.paths.config_dir = config_dir

    result = await process_check_files(ctx, doctypes=None)
    assert result == []
