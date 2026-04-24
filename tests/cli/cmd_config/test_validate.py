from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from docbuild.cli.cmd_cli import cli
from docbuild.cli.context import DocBuildContext


@pytest.fixture
def mock_ctx_obj():
    """Create a populated context object for validation tests."""
    ctx_obj = DocBuildContext()
    ctx_obj.appconfig = MagicMock()
    ctx_obj.appconfigfiles = (Path("app.toml"),)
    ctx_obj.envconfig = MagicMock()
    ctx_obj.envconfigfiles = (Path("env.toml"),)
    ctx_obj.doctypes = []
    return ctx_obj


@patch("docbuild.cli.cmd_cli.initialize_config")
@patch("docbuild.cli.cmd_config.validate.validate_portal_content", new_callable=AsyncMock)
@patch("docbuild.cli.cmd_config.validate.validate_app_settings")
@patch("docbuild.cli.cmd_config.validate.validate_env_settings")
def test_config_validate_success(mock_env, mock_app, mock_portal, mock_init, runner, mock_ctx_obj):
    """Test that config validate succeeds with valid configuration."""
    mock_app.return_value = True
    mock_env.return_value = True
    mock_portal.return_value = True

    result = runner.invoke(cli, ["config", "validate"], obj=mock_ctx_obj)

    assert result.exit_code == 0
    assert "Running Full Configuration Validation" in result.output
