"""Tests for the ``docbuild check files`` output."""

from collections import Counter
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from docbuild.cli.cmd_check import check_files, print_results, print_summary


@pytest.fixture
def mock_app_ctx():
    """Return a context whose environment paths point to fake files."""
    ctx = MagicMock()
    ctx.envconfig.paths.main_portal_config = Path("portal.xml")
    ctx.envconfig.paths.repo_dir = Path("repos")
    return ctx


def test_print_results_tree_and_summary(capsys):
    """Results are grouped per product/docset/lang with a summary line."""
    results = [
        ("sles/16.0/en-us", "DC-keg", "gh://suse/doc-modular", "missing"),
        ("sles/16.0/en-us", "sles", "", "linked"),
        ("sles/16.0/en-us", "DC-SLE", "gh://suse/x", "found"),
        ("sles/16.0/de-de", "DC-SLE", "gh://suse/x", "skipped"),
    ]
    print_results(results)
    print_summary(Counter(status for *_, status in results))

    out = capsys.readouterr().out
    assert "DC-keg" in out
    assert "[gh://suse/doc-modular]" in out
    assert "Found 1 file, 1 skipped, 1 error." in out


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("found", "Found 1 file, 0 skipped, 0 errors."),
        ("missing", "Found 0 files, 0 skipped, 1 error."),
        ("skipped", "Found 0 files, 1 skipped, 0 errors."),
    ],
)
def test_print_results_pluralization(capsys, status, expected):
    """The summary uses singular and plural forms correctly."""
    print_summary(Counter({status: 1}))

    assert expected in capsys.readouterr().out


def test_print_results_empty(capsys):
    """An empty result set still prints a summary."""
    print_summary(Counter())

    assert "Found 0 files, 0 skipped, 0 errors." in capsys.readouterr().out


@patch("docbuild.cli.cmd_check.check_repository_files")
def test_check_files_fails_on_missing(mock_check, runner, mock_app_ctx):
    """The command exits with an error when a file is missing."""
    mock_check.return_value = [("sles/16.0/en-us", "DC-keg", "gh://suse/x", "missing")]

    result = runner.invoke(check_files, [], obj=mock_app_ctx)

    assert result.exit_code == 1
    assert "1 file(s) missing" in result.output


@patch("docbuild.cli.cmd_check.check_repository_files")
def test_check_files_succeeds_without_missing(mock_check, runner, mock_app_ctx):
    """The command exits successfully when nothing is missing."""
    mock_check.return_value = [("sles/16.0/en-us", "DC-SLE", "gh://suse/x", "found")]

    result = runner.invoke(check_files, [], obj=mock_app_ctx)

    assert result.exit_code == 0


def test_check_files_requires_environment(runner):
    """The command fails clearly when no environment configuration is loaded."""
    ctx = MagicMock(envconfig=None)

    result = runner.invoke(check_files, [], obj=ctx)

    assert result.exit_code != 0
    assert "Environment configuration is missing" in result.output
