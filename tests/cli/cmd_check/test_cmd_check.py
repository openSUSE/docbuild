from unittest.mock import AsyncMock, MagicMock, patch

from click.testing import CliRunner
import pytest

from docbuild.cli.cmd_check.__init__ import check_files
from docbuild.cli.context import DocBuildContext
from docbuild.tasks.check import FileCheckResult


@pytest.fixture
def context_with_paths():
    """Provides a DocBuildContext with mocked envconfig paths."""
    ctx = DocBuildContext()
    ctx.envconfig = MagicMock()
    ctx.envconfig.paths.main_portal_config = "dummy_portal.xml"
    ctx.envconfig.paths.repo_dir = "dummy_repo_dir"
    ctx.envconfig.paths.prebuilt_dir = "dummy_prebuilt_dir"
    return ctx


@patch("docbuild.cli.cmd_check.__init__.check_repository_files", new_callable=AsyncMock)
def test_check_files_with_doctypes(mock_task, runner: CliRunner, context_with_paths):
    """Passing doctypes forwards them to the task."""
    mock_task.return_value = {}

    result = runner.invoke(check_files, ["sles/16.0/en-us"], obj=context_with_paths)

    assert result.exit_code == 0


@patch("docbuild.cli.cmd_check.__init__.check_repository_files", new_callable=AsyncMock)
def test_check_files_all(mock_task, runner: CliRunner, context_with_paths):
    """--all forwards no explicit doctypes (the task checks everything)."""
    mock_task.return_value = {}

    result = runner.invoke(check_files, ["--all"], obj=context_with_paths)

    assert result.exit_code == 0


@patch("docbuild.cli.cmd_check.__init__.check_repository_files", new_callable=AsyncMock)
def test_check_files_reports_missing_files(mock_task, runner: CliRunner, context_with_paths):
    """Missing files are reported as a ClickException (exit code 1)."""
    mock_task.return_value = {
        "sles/16.0/en-us": [FileCheckResult("sles/16.0/en-us", "DC-fake", "error")]
    }

    result = runner.invoke(check_files, ["--all"], obj=context_with_paths)

    assert result.exit_code == 1
    assert "DC-fake" in result.output


@patch("docbuild.cli.cmd_check.__init__.check_repository_files", new_callable=AsyncMock)
def test_check_files_groups_by_repo_branch(mock_task, runner: CliRunner, context_with_paths):
    """Files are grouped under a REPO/BRANCH node; repo-less files stay direct (#695)."""
    mock_task.return_value = {
        "sles/16.0/en-us": [
            FileCheckResult("sles/16.0/en-us", "DC-a", "found", repo="gh://mock/repo", branch="main"),
            FileCheckResult("sles/16.0/en-us", "DC-b", "error", repo="gh://mock/repo", branch="main"),
            FileCheckResult("sles/16.0/en-us", "DC-prebuilt", "found", is_prebuilt=True),
        ]
    }

    result = runner.invoke(check_files, ["--all"], obj=context_with_paths)

    assert result.exit_code == 1
    assert "gh://mock/repo/main" in result.output
    assert "DC-a" in result.output
    assert "DC-b" in result.output
    assert "DC-prebuilt" in result.output
