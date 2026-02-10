from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from docbuild.cli.cmd_check.process import (
    _extract_deliverables,
    _group_by_repo,
    process_check_files,
)


@pytest.fixture
def mock_xml_config(tmp_path):
    """Creates a temporary XML directory with a valid docset config."""
    config_dir = tmp_path / "config.d"
    config_dir.mkdir()
    xml_file = config_dir / "test_docset.xml"
    # Note: Using the structure the code expects (xpath //deliverable and ancestor lookups)
    xml_file.write_text("""
    <product>
        <docset>
            <builddocs>
                <git remote="https://github.com/openSUSE/doc-kit.git" />
                <language lang="en-us">
                    <deliverable>
                        <dc>README.md</dc>
                        <branch>main</branch>
                    </deliverable>
                </language>
            </builddocs>
        </docset>
    </product>
    """)
    return config_dir

def test_extract_deliverables(mock_xml_config):
    """Verify that every <deliverable> node is found regardless of hierarchy."""
    deliverables = _extract_deliverables(mock_xml_config)
    assert len(deliverables) == 1
    assert deliverables[0].find("dc").text == "README.md"

def test_group_by_repo(mock_xml_config):
    """Verify deliverables are correctly grouped by (repo, branch)."""
    deliverables = _extract_deliverables(mock_xml_config)
    groups = _group_by_repo(deliverables)

    key = ("https://github.com/openSUSE/doc-kit.git", "main")
    assert key in groups
    assert "README.md" in groups[key]

@pytest.mark.asyncio
@patch("docbuild.cli.cmd_check.process.ManagedGitRepo")
async def test_process_check_files_all_found(mock_repo_class, mock_xml_config, tmp_path):
    """Test full process when all files exist in the repo."""
    # Setup ManagedGitRepo Mock
    mock_repo = AsyncMock()
    mock_repo.clone_bare.return_value = True
    mock_repo.ls_tree.return_value = ["README.md", "LICENSE"]
    mock_repo_class.return_value = mock_repo

    # Setup Click/Context Mock
    ctx = MagicMock()
    ctx.envconfig.paths.config_dir = str(mock_xml_config)
    ctx.envconfig.paths.repo_dir = str(tmp_path / "repos")

    success = await process_check_files(ctx)

    assert success is True
    mock_repo.clone_bare.assert_called_once()
    mock_repo.ls_tree.assert_called_with("main")

@pytest.mark.asyncio
@patch("docbuild.cli.cmd_check.process.ManagedGitRepo")
async def test_process_check_files_missing(mock_repo_class, mock_xml_config, tmp_path):
    """Test full process when a file is missing in the repo."""
    mock_repo = AsyncMock()
    mock_repo.clone_bare.return_value = True
    mock_repo.ls_tree.return_value = ["LICENSE"] # README.md is missing
    mock_repo_class.return_value = mock_repo

    ctx = MagicMock()
    ctx.envconfig.paths.config_dir = str(mock_xml_config)
    ctx.envconfig.paths.repo_dir = str(tmp_path / "repos")

    success = await process_check_files(ctx)

    assert success is False

def test_extract_deliverables_empty_dir(tmp_path):
    """Verify behavior when no XML files are present."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    deliverables = _extract_deliverables(empty_dir)
    assert deliverables == []
