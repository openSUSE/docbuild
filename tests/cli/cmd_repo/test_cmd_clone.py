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


@pytest.mark.parametrize(
    ("args", "expected_repos"),
    [
        (["org/repo1"], ("org/repo1",)),
        (["org/repo1", "org/repo2"], ("org/repo1", "org/repo2")),
        (["--all"], ()),
    ],
    ids=["single_repo", "multiple_repos", "all_flag"],
)
@pytest.mark.parametrize("exit_code", [0, 1])
def test_clone_command_delegates_to_task(
    runner, tmp_path, mock_clone_repositories, args, expected_repos, exit_code
):
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
    mock_clone_repositories.return_value = exit_code
    result = runner.invoke(clone, args, obj=context)

    # Verify the CLI executed without errors
    assert result.exit_code == exit_code

    # Verify our business logic was called with the correct extracted arguments
    mock_clone_repositories.assert_awaited_once_with(
        config_dir / "portal.xml",
        repo_dir,
        expected_repos,
    )


@pytest.mark.parametrize(
    ("args", "message"),
    [
        ([], "Provide at least one repository argument or --all."),
        (
            ["org/repo1", "--all"],
            "Repository arguments and --all are mutually exclusive.",
        ),
        (
            ["--all", "org/repo1"],
            "Repository arguments and --all are mutually exclusive.",
        ),
        (
            ["org/repo1", "org/repo2", "--all"],
            "Repository arguments and --all are mutually exclusive.",
        ),
    ],
    ids=["missing_all", "repo_then_all", "all_then_repo", "multi_repos_with_all"],
)
@pytest.mark.parametrize("has_envconfig", [False, True])
def test_clone_command_rejects_invalid_selection(
    runner, mock_clone_repositories, args, message, has_envconfig
):
    """Reject invalid selections before configuration access or cloning."""
    context = DocBuildContext()
    context.envconfig = MagicMock() if has_envconfig else None

    result = runner.invoke(clone, args, obj=context)

    assert result.exit_code == 2
    assert "Usage:" in result.output
    assert message in result.output
    mock_clone_repositories.assert_not_called()


def test_clone_command_help(runner, mock_clone_repositories):
    """Explain both mutually exclusive modes without starting cloning."""
    result = runner.invoke(clone, ["--help"])

    assert result.exit_code == 0
    output = " ".join(result.output.split())
    assert "REPOS" in output
    assert "--all" in output
    assert "exactly one mode" in output
    assert "repository arguments" in output
    assert "all configured repositories" in output
    mock_clone_repositories.assert_not_called()


@pytest.mark.parametrize(
    "args",
    [
        ["org/repo1"],
        ["--all"],
    ],
    ids=["explicit_repo", "all_flag"],
)
def test_clone_command_fails_missing_envconfig(runner, args):
    """Test that the clone command aborts cleanly if envconfig is None."""
    context = DocBuildContext()
    context.envconfig = None

    result = runner.invoke(clone, args, obj=context)

    assert result.exit_code != 0
    assert "Environment configuration is missing" in result.output
