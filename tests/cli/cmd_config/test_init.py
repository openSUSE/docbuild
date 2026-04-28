from pathlib import Path
from unittest.mock import MagicMock, patch

from docbuild.cli.cmd_cli import cli


@patch("docbuild.cli.cmd_cli.load_app_config")
@patch("docbuild.cli.cmd_cli.load_env_config")
@patch("docbuild.cli.cmd_cli.setup_logging")
def test_config_list_default(mock_logging, mock_env, mock_app, runner):
    """Test that 'config list' shows both app and env config by default."""
    mock_ctx = MagicMock()
    mock_ctx.appconfig.model_dump.return_value = {"app_key": "app_val"}
    mock_ctx.envconfig.model_dump.return_value = {"env_key": "env_val"}
    # Mock this to prevent the PID lock AttributeError
    mock_ctx.envconfigfiles = [Path("env.toml")]

    result = runner.invoke(cli, ["config", "list"], obj=mock_ctx)

    assert result.exit_code == 0
    assert "app_key" in result.output
    assert "env_key" in result.output

@patch("docbuild.cli.cmd_cli.load_app_config")
@patch("docbuild.cli.cmd_cli.load_env_config")
@patch("docbuild.cli.cmd_cli.setup_logging")
def test_config_list_flat(mock_logging, mock_env, mock_app, runner):
    """Test that 'config list --flat' shows dotted notation."""
    mock_ctx = MagicMock()
    mock_ctx.appconfig.model_dump.return_value = {"logging": {"level": "INFO"}}
    mock_ctx.envconfig = None
    mock_ctx.envconfigfiles = []

    result = runner.invoke(cli, ["config", "list", "--app", "--flat"], obj=mock_ctx)

    assert result.exit_code == 0
    assert "app.logging.level" in result.output
    assert "'INFO'" in result.output

@patch("docbuild.cli.cmd_cli.load_app_config")
@patch("docbuild.cli.cmd_cli.load_env_config")
@patch("docbuild.cli.cmd_cli.setup_logging")
def test_config_validate_display(mock_logging, mock_env, mock_app, runner):
    """Test that 'config validate' shows the success panel."""
    mock_ctx = MagicMock()
    # Use Path objects instead of strings to satisfy the PidFileLock logic
    mock_ctx.appconfigfiles = [Path("app.toml")]
    mock_ctx.envconfigfiles = [Path("env.toml")]
    mock_ctx.envconfig_from_defaults = False

    result = runner.invoke(cli, ["config", "validate"], obj=mock_ctx)

    assert result.exit_code == 0
    assert "Configuration is valid" in result.output
