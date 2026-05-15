"""Tests for the portal list command."""

from unittest.mock import MagicMock

from click.testing import CliRunner

from docbuild.cli.cmd_portal.cmd_list import list_cmd
from docbuild.cli.context import DocBuildContext


def test_portal_list_help() -> None:
    """Test that the help menu renders correctly for 'portal list'."""
    runner = CliRunner()
    result = runner.invoke(list_cmd, ["--help"])

    assert result.exit_code == 0
    assert "List products, docsets, and deliverables from the portal config." in result.output
    # Click wraps long help text, so we assert the parts separately
    assert "Format:" in result.output
    assert "[PRODUCT]" in result.output


def test_portal_list_no_main_config(tmp_path) -> None:
    """Test that the command gracefully aborts if portal.xml is not found."""
    runner = CliRunner()

    # Create a dummy context with an empty temporary directory
    mock_ctx = DocBuildContext()
    mock_ctx.envconfig = MagicMock()
    mock_ctx.envconfig.paths.config_dir.expanduser.return_value = tmp_path

    # Invoke the command with the mocked context
    result = runner.invoke(list_cmd, obj=mock_ctx)

    # It should exit with a non-zero status code (Abort)
    assert result.exit_code != 0
    # Rich line-wraps long paths, so we only check the prefix of our new error message
    assert "Error: Main portal config not found at" in result.output


def test_portal_list_invalid_doctype() -> None:
    """Test that the command gracefully aborts if an invalid doctype is passed."""
    runner = CliRunner()
    mock_ctx = DocBuildContext()

    # Invoke with a badly formatted doctype string that fails parsing
    result = runner.invoke(list_cmd, ["invalid_doctype_format!"], obj=mock_ctx)

    assert result.exit_code != 0
    assert "Error parsing doctype:" in result.output
