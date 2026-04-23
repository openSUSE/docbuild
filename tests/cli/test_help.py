import sys
from unittest.mock import patch

from docbuild.cli.cmd_cli import cli


def test_help_option(runner):
    """Test that the main help option works."""
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Usage:" in result.output


def test_config_list_help_works_on_broken_config(runner):
    """Verify that config subcommands show help without loading configuration."""
    # We mock sys.argv so the 'if' check in cmd_cli.py sees the help flag
    # and we patch load_app_config to ensure it's never called.
    test_args = ["docbuild", "config", "list", "--help"]

    with patch.object(sys, 'argv', test_args):
        with patch("docbuild.cli.cmd_cli.load_app_config") as mock_load:
            result = runner.invoke(cli, ["config", "list", "--help"])

    assert result.exit_code == 0
    assert "Usage: docbuild config list" in result.output

    # This is the real test: did we bypass the loader?
    mock_load.assert_not_called()
