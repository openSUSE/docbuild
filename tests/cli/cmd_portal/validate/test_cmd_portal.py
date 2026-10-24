"""Tests for the 'docbuild portal validate' command."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from docbuild.cli.cmd_portal import cmd_validate as cmd_validate_module
from docbuild.cli.cmd_portal.cmd_validate import validate
from docbuild.cli.context import DocBuildContext


@pytest.fixture
def mock_validate_portal_config(monkeypatch) -> AsyncMock:
    """Fixture to mock the validate_portal_config task."""
    mock = AsyncMock(return_value=0)
    monkeypatch.setattr(cmd_validate_module, "validate_portal_config", mock)
    return mock


def test_validate_command_delegates_to_task(runner, tmp_path, mock_validate_portal_config):
    """Test that the validate CLI command correctly calls the task module."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    mock_env = MagicMock()
    mock_env.paths.main_portal_config = config_dir / "portal.xml"
    mock_env.paths.portal_rncschema = config_dir / "schema.rnc"

    context = DocBuildContext()
    context.envconfig = mock_env
    context.verbose = 2

    result = runner.invoke(validate, [], obj=context)

    assert result.exit_code == 0
    mock_validate_portal_config.assert_awaited_once_with(
        Path(config_dir / "portal.xml"),
        Path(config_dir / "schema.rnc"),
        verbose=2
    )

def test_validate_command_with_overrides(runner, tmp_path, mock_validate_portal_config):
    """Test that CLI flags override the environment configuration."""
    mock_env = MagicMock()
    mock_env.paths.main_portal_config = "/default/portal.xml"
    mock_env.paths.portal_rncschema = "/default/schema.rnc"

    context = DocBuildContext()
    context.envconfig = mock_env
    context.verbose = 0

    custom_portal = tmp_path / "custom_portal.xml"
    custom_portal.touch()
    custom_schema = tmp_path / "custom_schema.rnc"
    custom_schema.touch()

    result = runner.invoke(
        validate,
        ["-M", str(custom_portal), "-S", str(custom_schema)],
        obj=context
    )

    assert result.exit_code == 0
    mock_validate_portal_config.assert_awaited_once_with(
        custom_portal,
        custom_schema,
        verbose=0
    )


def test_validate_command_fails_missing_envconfig(runner):
    """Test that the validate command aborts cleanly if envconfig is None."""
    context = DocBuildContext()
    context.envconfig = None

    result = runner.invoke(validate, [], obj=context)

    assert result.exit_code != 0
    assert "Environment configuration is missing" in result.output
