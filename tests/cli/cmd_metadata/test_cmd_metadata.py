"""CLI-level tests for the ``docbuild metadata`` command.

Implementation tests (deliverables, daps, repos, manifest, runner) have been
moved to ``tests/tasks/metadata/``.  This module covers only Click wiring:
the command is importable and its help text is accessible.
"""

from click.testing import CliRunner

from docbuild.cli.cmd_metadata import metadata


def test_metadata_help_exits_zero():
    """Verify that ``docbuild metadata --help`` exits successfully."""
    runner = CliRunner()
    result = runner.invoke(metadata, ["--help"])
    assert result.exit_code == 0
    assert "exitfirst" in result.output.lower() or "--exitfirst" in result.output
