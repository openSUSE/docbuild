"""Tests for the `docbuild build dir` command."""

from click.testing import CliRunner

from docbuild.cli.cmd_cli import cli


def test_build_dir_prints_target_base_dir(runner: CliRunner) -> None:
    """Verify that build dir prints the configured target base directory."""
    result = runner.invoke(cli, ["build", "dir"])
    assert result.exit_code == 0
    assert result.output.strip() != ""
    # The output should be a valid absolute path
    assert result.output.strip().startswith("/")
