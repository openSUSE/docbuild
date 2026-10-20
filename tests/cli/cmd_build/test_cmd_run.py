"""Tests for docbuild build run subcommand."""

from click.testing import CliRunner

from docbuild.cli.cmd_build import build
from docbuild.cli.cmd_build.cmd_run import run


def test_build_group_registers_run_command():
    """Verify 'run' is registered under the 'build' click group."""
    assert "run" in build.commands
    assert build.commands["run"] is run


def test_build_run_help():
    """Verify 'docbuild build run --help' displays descriptions and options."""
    runner = CliRunner()
    result = runner.invoke(build, ["run", "--help"])

    assert result.exit_code == 0
    assert "Build a documentation deliverables from source" in result.output
    assert "--skip-repo-update" in result.output
    assert "--skip-metadata" in result.output


def test_build_group_help_shows_run_subcommand():
    """Verify 'docbuild build --help' lists 'run' as an available subcommand."""
    runner = CliRunner()
    result = runner.invoke(build, ["--help"])

    assert result.exit_code == 0
    assert "run" in result.output
