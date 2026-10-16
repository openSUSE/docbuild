"""Tests for the 'docbuild repo clone' command."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from docbuild.cli.cmd_repo import cmd_clone as cmd_clone_module
from docbuild.cli.cmd_repo.cmd_clone import clone
from docbuild.cli.context import DocBuildContext


@pytest.fixture
def mock_clone_repositories(monkeypatch) -> AsyncMock:
    """Fixture to mock the clone_repositories task."""
    mock = AsyncMock(return_value=0)
    monkeypatch.setattr(cmd_clone_module, "clone_repositories", mock)
    return mock


def test_clone_command_delegates_to_task(runner, tmp_path, mock_clone_repositories):
    """Test that the clone CLI command correctly calls the task module."""
    # Setup dummy paths for the context
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    repo_dir = tmp_path / "repos"
    repo_dir.mkdir()

    # Use MagicMock to satisfy strict type checkers without defining dummy classes
    mock_env = MagicMock()
    mock_env.paths.main_portal_config = config_dir / "portal.xml"
    mock_env.paths.repo_dir = repo_dir

    # Initialize context and assign the mock directly to bypass __init__ type checking
    context = DocBuildContext()
    context.envconfig = mock_env

    # Call the CLI command with some repo arguments
    result = runner.invoke(clone, ["org/repo1", "org/repo2"], obj=context)

    # Verify the CLI executed without errors
    assert result.exit_code == 0

    # Verify our business logic was called with the correct extracted arguments
    mock_clone_repositories.assert_awaited_once_with(
        config_dir / "portal.xml",
        repo_dir,
        ("org/repo1", "org/repo2")
    )


def test_clone_command_fails_missing_envconfig(runner):
    """Test that the clone command aborts cleanly if envconfig is None."""
    context = DocBuildContext()
    context.envconfig = None

    result = runner.invoke(clone, ["org/repo1"], obj=context)

    assert result.exit_code != 0
    assert "Environment configuration is missing" in result.output


@pytest.fixture
def clone_context(tmp_path) -> DocBuildContext:
    """Fixture for a context whose envconfig points into a temporary directory."""
    mock_env = MagicMock()
    mock_env.paths.main_portal_config = tmp_path / "portal.xml"
    mock_env.paths.repo_dir = tmp_path / "repos"

    context = DocBuildContext()
    context.envconfig = mock_env
    return context


def test_clone_command_requires_repos_or_all(
    runner, clone_context, mock_clone_repositories
):
    """Test that the clone command does not clone anything without a selection."""
    result = runner.invoke(clone, [], obj=clone_context)

    assert result.exit_code == 2
    assert "--all" in result.output
    mock_clone_repositories.assert_not_awaited()


def test_clone_command_all_clones_every_repo(
    runner, clone_context, tmp_path, mock_clone_repositories
):
    """Test that --all passes an empty selection, which clones all repos."""
    result = runner.invoke(clone, ["--all"], obj=clone_context)

    assert result.exit_code == 0
    mock_clone_repositories.assert_awaited_once_with(
        tmp_path / "portal.xml", tmp_path / "repos", ()
    )


def test_clone_command_rejects_repos_with_all(
    runner, clone_context, mock_clone_repositories
):
    """Test that repositories and --all cannot be combined."""
    result = runner.invoke(clone, ["--all", "org/repo1"], obj=clone_context)

    assert result.exit_code == 2
    assert "--all" in result.output
    mock_clone_repositories.assert_not_awaited()
