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
    mock_ctx.envconfig = MagicMock()
    mock_ctx.envconfig.paths.tmp.log_dir = Path("/tmp")
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


def test_config_theme_cmd(runner):
    """Test that 'config theme' shows both Dark and Light presets."""
    result = runner.invoke(cli, ["config", "theme"])
    assert result.exit_code == 0
    assert "Built-in Theme Preset: Dark" in result.output
    assert "Built-in Theme Preset: Light" in result.output


def test_config_theme_cmd_preset_filter(runner):
    """Test that 'config theme --preset light' displays only the Light preset."""
    result = runner.invoke(cli, ["config", "theme", "--preset", "light"])
    assert result.exit_code == 0
    assert "Built-in Theme Preset: Light" in result.output
    assert "Built-in Theme Preset: Dark" not in result.output


@patch("docbuild.cli.cmd_cli.load_app_config")
@patch("docbuild.cli.cmd_cli.load_env_config")
@patch("docbuild.cli.cmd_cli.setup_logging")
def test_config_theme_cmd_with_active_config(mock_logging, mock_env, mock_app, runner):
    """Test that 'config theme' displays active configuration theme table."""
    mock_ctx = MagicMock()
    mock_ctx.appconfig.theme = {
        "header": "bold cyan",
        "error": "bold magenta",
        "warning": "bold yellow",
        "info": "bold bright_blue",
        "success": "bold green",
        "hint": "dim italic cyan",
        "muted": "dim white",
        "lang": "white",
        "product": "dim white",
        "docset": "blue",
    }
    mock_ctx.appconfigfiles = [Path("custom_app.toml")]
    mock_ctx.appconfig_from_defaults = False

    result = runner.invoke(cli, ["config", "theme"], obj=mock_ctx)
    assert result.exit_code == 0
    assert "Active Configuration Theme (custom_app.toml)" in result.output
    assert "bold magenta" in result.output


