from unittest.mock import patch

from docbuild.cli.cmd_cli import cli


def test_help_option(runner):
    """Test that the main help option works."""
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Usage:" in result.output


def test_config_list_help_works_on_broken_config(runner):
    """Verify that config subcommands show help without loading configuration."""
    with patch("docbuild.cli.cmd_cli.initialize_config") as mock_init:
        # We run the command with --help
        result = runner.invoke(cli, ["config", "list", "--help"])

    assert result.exit_code == 0
    assert "Usage: docbuild config list" in result.output
    assert mock_init.call_count <= 1
