from unittest.mock import AsyncMock, MagicMock, patch

from lxml import etree

from docbuild.cli.cmd_check import process
from docbuild.cli.cmd_check.process import (
    _group_by_repo,
    process_check_files,
)


def test_group_by_repo():
    """Verify deliverables are correctly grouped by (repo, branch)."""
    xml_content = """
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
    """
    # Note: process.py now uses local-name() so the test logic is namespace-resilient
    tree = etree.fromstring(xml_content)
    deliverables = tree.xpath("//deliverable")

    groups = _group_by_repo(deliverables)

    key = ("https://github.com/openSUSE/doc-kit.git", "main")
    assert key in groups
    assert "README.md" in groups[key]

@patch.object(process, "create_stitchfile", new_callable=AsyncMock)
@patch.object(process, "ManagedGitRepo")
async def test_process_check_files_all_found(mock_repo_class, mock_stitch, tmp_path):
    """Test full process when all files exist in the repo."""
    mock_tree = MagicMock()
    mock_tree.xpath.return_value = [MagicMock()]

    with patch("docbuild.cli.cmd_check.process._group_by_repo") as mock_group:
        mock_group.return_value = {("https://repo.git", "main"): ["README.md"]}
        mock_stitch.return_value = mock_tree

        mock_repo = AsyncMock()
        mock_repo.clone_bare.return_value = True
        mock_repo.ls_tree.return_value = ["README.md"]
        mock_repo_class.return_value = mock_repo

        ctx = MagicMock()
        config_dir = tmp_path / "config.d"
        config_dir.mkdir()
        (config_dir / "test.xml").write_text("<xml/>")
        ctx.envconfig.paths.config_dir = config_dir
        ctx.envconfig.paths.repo_dir = tmp_path / "repos"

        # Testing with optional doctype filter as well
        result = await process_check_files(ctx, doctype_filter="suse-ai/1.0/en-us")

        assert result == []
        mock_repo.clone_bare.assert_called_once()
        mock_repo.ls_tree.assert_called_with("main")

@patch.object(process, "create_stitchfile", new_callable=AsyncMock)
@patch.object(process, "ManagedGitRepo")
async def test_process_check_files_missing(mock_repo_class, mock_stitch, tmp_path):
    """Test full process when a file is missing in the repo."""
    with patch("docbuild.cli.cmd_check.process._group_by_repo") as mock_group:
        mock_group.return_value = {("https://repo.git", "main"): ["README.md"]}

        mock_tree = MagicMock()
        mock_tree.xpath.return_value = [MagicMock()]
        mock_stitch.return_value = mock_tree

        mock_repo = AsyncMock()
        mock_repo.clone_bare.return_value = True
        mock_repo.ls_tree.return_value = ["LICENSE"]
        mock_repo_class.return_value = mock_repo

        ctx = MagicMock()
        config_dir = tmp_path / "config.d"
        config_dir.mkdir()
        (config_dir / "test.xml").write_text("<xml/>")
        ctx.envconfig.paths.config_dir = config_dir
        ctx.envconfig.paths.repo_dir = tmp_path / "repos"

        result = await process_check_files(ctx)

        assert "README.md" in result

@patch.object(process, "create_stitchfile", new_callable=AsyncMock)
@patch.object(process, "ManagedGitRepo")
async def test_process_git_failure(mock_repo_class, mock_stitch, tmp_path):
    """Test coverage for the branch where Git cloning/fetching fails."""
    with patch("docbuild.cli.cmd_check.process._group_by_repo") as mock_group:
        mock_group.return_value = {("https://bad-repo.git", "main"): ["README.md"]}

        mock_tree = MagicMock()
        mock_tree.xpath.return_value = [MagicMock()]
        mock_stitch.return_value = mock_tree

        mock_repo = AsyncMock()
        mock_repo.clone_bare.return_value = False # Simulate failure
        mock_repo_class.return_value = mock_repo

        ctx = MagicMock()
        config_dir = tmp_path / "config.d"
        config_dir.mkdir()
        (config_dir / "test.xml").write_text("<xml/>")
        ctx.envconfig.paths.config_dir = config_dir
        ctx.envconfig.paths.repo_dir = tmp_path / "repos"

        result = await process_check_files(ctx)

        # If Git fails, the file should be reported as missing/inaccessible
        assert "README.md" in result

@patch.object(process, "create_stitchfile", new_callable=AsyncMock)
async def test_process_no_deliverables_xml(mock_stitch, tmp_path):
    """Test path where XML exists but contains no deliverables."""
    mock_tree = MagicMock()
    mock_tree.xpath.return_value = [] # No deliverables found
    mock_stitch.return_value = mock_tree

    ctx = MagicMock()
    config_dir = tmp_path / "config.d"
    config_dir.mkdir()
    (config_dir / "test.xml").write_text("<xml/>")
    ctx.envconfig.paths.config_dir = config_dir

    result = await process_check_files(ctx)
    assert result == []

@patch.object(process, "create_stitchfile", new_callable=AsyncMock)
async def test_process_no_xml_files(mock_stitch, tmp_path):
    """Verify behavior when no XML files are present at all."""
    ctx = MagicMock()
    config_dir = tmp_path / "empty"
    config_dir.mkdir()
    ctx.envconfig.paths.config_dir = config_dir

    result = await process_check_files(ctx)
    assert result == []
