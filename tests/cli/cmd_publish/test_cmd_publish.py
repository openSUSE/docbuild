"""Tests for the docbuild publish command."""

from unittest.mock import Mock

from click.testing import CliRunner

from docbuild.cli.cmd_cli import cli
from docbuild.cli.context import DocBuildContext


def test_publish_help() -> None:
    """Test publish --help output."""
    runner = CliRunner()
    result = runner.invoke(cli, ["publish", "--help"])
    assert result.exit_code == 0
    assert "Publish documentation deliverables" in result.output
    assert "run" in result.output


def test_publish_run_missing_remote() -> None:
    """Test publish run aborts if remote server and path are not configured."""
    runner = CliRunner()

    mock_ctx = Mock(spec=DocBuildContext)
    mock_ctx.envconfig.remote.server = None
    mock_ctx.envconfig.remote.path = None

    result = runner.invoke(cli, ["publish", "run", "sles/16.0/en-us"], obj=mock_ctx)
    assert result.exit_code != 0
    assert "The [remote] section is not configured" in result.output
