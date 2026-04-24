from unittest.mock import MagicMock

from rich.console import Console

from docbuild.cli.cmd_config.validate.app import validate_app_settings


def test_validate_app_settings_success():
    """Verify returns True and prints files when appconfig exists."""
    # Arrange
    mock_ctx = MagicMock()
    mock_ctx.appconfig = MagicMock()
    mock_ctx.appconfigfiles = ["/path/to/docbuild.toml"]
    console = Console()

    # Act
    result = validate_app_settings(mock_ctx, console)

    # Assert
    assert result is True


def test_validate_app_settings_no_config():
    """Verify returns False when appconfig is missing."""
    # Arrange
    mock_ctx = MagicMock()
    mock_ctx.appconfig = None
    console = Console()

    # Act
    result = validate_app_settings(mock_ctx, console)

    # Assert
    assert result is False
