from unittest.mock import MagicMock

from rich.console import Console

from docbuild.cli.cmd_config.validate.env import validate_env_settings


def test_validate_env_settings_success():
    """Verify returns True and prints files when envconfig exists."""
    # Arrange
    mock_ctx = MagicMock()
    mock_ctx.envconfig = MagicMock()
    mock_ctx.envconfigfiles = ["/path/to/env.toml"]
    console = Console()

    # Act
    result = validate_env_settings(mock_ctx, console)

    # Assert
    assert result is True


def test_validate_env_settings_defaults():
    """Verify handles the case where env uses internal defaults."""
    # Arrange
    mock_ctx = MagicMock()
    mock_ctx.envconfig = MagicMock()
    mock_ctx.envconfigfiles = []
    mock_ctx.envconfig_from_defaults = True
    console = Console()

    # Act
    result = validate_env_settings(mock_ctx, console)

    # Assert
    assert result is True
