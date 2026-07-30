"""Tests for the 'docbuild metadata' command."""

from unittest.mock import AsyncMock, MagicMock

import pytest

import docbuild.cli.cmd_metadata as cmd_metadata_module
from docbuild.cli.cmd_metadata import metadata
from docbuild.cli.context import DocBuildContext


@pytest.fixture
def mock_generate_metadata(monkeypatch) -> AsyncMock:
    """Fixture to mock the generate_metadata task."""
    mock = AsyncMock(return_value=0)
    monkeypatch.setattr(cmd_metadata_module, "generate_metadata", mock)
    return mock


def test_metadata_command_delegates_to_task(runner, tmp_path, mock_generate_metadata):
    """Test that the metadata CLI command correctly calls the task module."""
    mock_env = MagicMock()
    mock_env.paths.config_dir = tmp_path / "config"
    mock_env.paths.main_portal_config = tmp_path / "portal.xml"
    mock_env.paths.tmp.tmp_metadata_dir = tmp_path / "tmp_meta"
    mock_env.paths.repo_dir = tmp_path / "repos"
    mock_env.paths.tmp_repo_dir = tmp_path / "tmp_repos"
    mock_env.paths.meta_cache_dir = tmp_path / "cache_meta"
    mock_env.build.daps.meta = "daps --meta"

    context = DocBuildContext()
    context.envconfig = mock_env

    result = runner.invoke(metadata, [], obj=context)

    assert result.exit_code == 0
    mock_generate_metadata.assert_awaited_once_with(
        main_portal_config=tmp_path / "portal.xml",
        tmp_metadata_dir=tmp_path / "tmp_meta",
        repo_dir=tmp_path / "repos",
        tmp_repo_dir=tmp_path / "tmp_repos",
        meta_cache_dir=tmp_path / "cache_meta",
        dapsmetatmpl="daps --meta",
        doctypes=[],
        exitfirst=False,
        skip_repo_update=False,
    )


def test_metadata_command_with_flags(runner, tmp_path, mock_generate_metadata):
    """Test that CLI flags are properly passed to the task."""
    mock_env = MagicMock()
    mock_env.paths.main_portal_config = tmp_path / "portal.xml"

    context = DocBuildContext()
    context.envconfig = mock_env

    result = runner.invoke(
        metadata,
        ["--exitfirst", "--skip-repo-update"],
        obj=context
    )

    assert result.exit_code == 0
    mock_generate_metadata.assert_awaited_once()
    kwargs = mock_generate_metadata.call_args.kwargs
    assert kwargs["exitfirst"] is True
    assert kwargs["skip_repo_update"] is True
