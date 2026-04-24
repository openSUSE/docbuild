from unittest.mock import AsyncMock, MagicMock, patch

from click.testing import CliRunner

from docbuild.cli.cmd_cli import cli


@patch("docbuild.cli.cmd_cli.initialize_config")
@patch("docbuild.cli.cmd_config.validate.validate_portal_content", new_callable=AsyncMock)
@patch("docbuild.cli.cmd_config.validate.validate_app_settings")
@patch("docbuild.cli.cmd_config.validate.validate_env_settings")
def test_validate_orchestration_success(mock_env, mock_app, mock_portal, mock_init):
    """Verify that the validate command calls all three sub-validators."""
    # 1. Setup Mocks
    mock_app.return_value = True
    mock_env.return_value = True
    mock_portal.return_value = True

    # 2. Create a mock context
    mock_context = MagicMock()

    runner = CliRunner()

    # 3. Act
    result = runner.invoke(cli, ["config", "validate"], obj=mock_context)

    # 4. Assert
    assert result.exit_code == 0, f"Command failed with output: {result.output}"
    assert "Running Full Configuration Validation" in result.output

    mock_app.assert_called_once()
    mock_env.assert_called_once()
    mock_portal.assert_awaited_once()
