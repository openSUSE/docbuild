"""Tests for the docbuild build index CLI command router."""

from click.testing import CliRunner

from docbuild.cli.cmd_build.cmd_index import index


def test_build_index_requires_doctype() -> None:
    """Verify command fails when no DOCTYPE argument is supplied."""
    runner = CliRunner()
    result = runner.invoke(index, [])
    assert result.exit_code != 0
    assert "Missing argument" in result.output or "DOCTYPES" in result.output


def test_build_index_help() -> None:
    """Verify --help flag displays documentation and options."""
    runner = CliRunner()
    result = runner.invoke(index, ["--help"])
    assert result.exit_code == 0
    assert "--keep-index" in result.output
