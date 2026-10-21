"""Tests for the 'docbuild check files' command."""

from unittest.mock import AsyncMock, MagicMock, patch

from click.testing import CliRunner
import pytest

import docbuild.cli.cmd_check as cmd_check_module
from docbuild.cli.cmd_check import check_files
from docbuild.cli.context import DocBuildContext


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def context_with_paths(context: DocBuildContext, tmp_path) -> DocBuildContext:
    """Extend the shared ``context`` fixture with environment paths."""
    env = MagicMock()
    env.paths.main_portal_config = tmp_path / "portal.xml"
    env.paths.repo_dir = tmp_path / "repos"

    context.envconfig = env
    return context


def test_check_files_requires_doctypes_or_all(runner, context_with_paths):
    """No arguments must fail politely instead of doing a hidden full check."""
    result = runner.invoke(check_files, [], obj=context_with_paths)

    assert result.exit_code == 2
    assert "one or more doctypes" in result.output
    assert "--all" in result.output


def test_check_files_all_and_doctypes_are_mutually_exclusive(
    runner, context_with_paths
):
    """Using --all together with doctypes must be rejected."""
    result = runner.invoke(
        check_files, ["--all", "sles/16.0/en-us"], obj=context_with_paths
    )

    assert result.exit_code == 2
    assert "cannot be combined" in result.output


@patch.object(cmd_check_module, "check_repository_files", new_callable=AsyncMock)
def test_check_files_with_doctypes(mock_task, runner, context_with_paths):
    """Passing doctypes forwards them to the task."""
    mock_task.return_value = []

    result = runner.invoke(check_files, ["sles/16.0/en-us"], obj=context_with_paths)

    assert result.exit_code == 0
    mock_task.assert_awaited_once()
    passed_doctypes = mock_task.call_args.args[2]
    assert passed_doctypes is not None
    assert passed_doctypes[0].product.acronym == "sles"


@patch.object(cmd_check_module, "check_repository_files", new_callable=AsyncMock)
def test_check_files_all(mock_task, runner, context_with_paths):
    """--all forwards no explicit doctypes (the task checks everything)."""
    mock_task.return_value = []

    result = runner.invoke(check_files, ["--all"], obj=context_with_paths)

    assert result.exit_code == 0
    mock_task.assert_awaited_once()
    assert mock_task.call_args.args[2] is None


@patch.object(cmd_check_module, "check_repository_files", new_callable=AsyncMock)
def test_check_files_reports_missing_files(mock_task, runner, context_with_paths):
    """Missing files are reported as a ClickException (exit code 1)."""
    mock_task.return_value = ["[gh://org/repo] sles/16.0/en-us:DC-fake"]

    result = runner.invoke(check_files, ["--all"], obj=context_with_paths)

    assert result.exit_code == 1
    assert "DC-fake" in result.output


def test_check_files_missing_envconfig(runner):
    """A missing environment configuration is reported clearly."""
    result = runner.invoke(check_files, ["--all"], obj=DocBuildContext())

    assert result.exit_code == 1
    assert "Environment configuration is missing" in result.output
