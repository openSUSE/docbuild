"""Tests for the docbuild doctor command."""

from typing import Any
from unittest.mock import MagicMock, patch

from click.testing import CliRunner
import pytest

from docbuild.cli import cmd_doctor
from docbuild.cli.cmd_cli import cli


@pytest.mark.parametrize(
    ("dep_result", "expected_exit_code", "expected_status", "expected_summary"),
    [
        pytest.param(
            {
                "name": "mock-tool",
                "required": ">=1.0",
                "found": "2.0",
                "is_installed": True,
                "is_valid": True,
                "message": "OK",
            },
            0,
            "✓ OK",
            "All system dependencies look good!",
            id="all_valid",
        ),
        pytest.param(
            {
                "name": "missing-tool",
                "required": ">=1.0",
                "found": None,
                "is_installed": False,
                "is_valid": False,
                "message": "Not found in PATH",
            },
            1,
            "✗ Missing",
            "Some required system dependencies are missing or outdated.",
            id="missing_tool",
        ),
        pytest.param(
            {
                "name": "outdated-tool",
                "required": ">=4.0",
                "found": "3.3.0",
                "is_installed": True,
                "is_valid": False,
                "message": "Version too old",
            },
            1,
            "✗ Version too old",
            "Some required system dependencies are missing or outdated.",
            id="version_mismatch",
        ),
        pytest.param(
            {
                "name": "warning-tool",
                "required": ">=2.9.0",
                "found": "Unknown",
                "is_installed": True,
                "is_valid": True,
                "message": "Warning: Could not determine version",
            },
            0,
            "⚠ Warning: Could not determine version",
            "All system dependencies look good!",
            id="warning_only_non_fatal",
        ),
    ],
)
@patch.object(cmd_doctor, "check_dependencies")
def test_doctor_command_status_handling(
    mock_check: MagicMock,
    runner: CliRunner,
    dep_result: dict[str, Any],
    expected_exit_code: int,
    expected_status: str,
    expected_summary: str,
) -> None:
    """Test doctor exit codes and status labels across all dependency states in isolation."""
    mock_check.return_value = [dep_result]
    result = runner.invoke(cmd_doctor.doctor)

    assert result.exit_code == expected_exit_code
    assert dep_result["name"] in result.output
    assert expected_status in result.output
    assert expected_summary in result.output


@pytest.mark.parametrize(
    ("dep_overrides", "expected_required", "expected_found"),
    [
        pytest.param(
            {"required": None, "found": "1.0"},
            "Any",
            "1.0",
            id="fallback_required_any",
        ),
        pytest.param(
            {"required": ">=1.0", "found": None},
            ">=1.0",
            "---",
            id="fallback_found_dashes",
        ),
    ],
)
@patch.object(cmd_doctor, "check_dependencies")
def test_doctor_command_fallback_values(
    mock_check: MagicMock,
    runner: CliRunner,
    dep_overrides: dict[str, Any],
    expected_required: str,
    expected_found: str,
) -> None:
    """Test doctor fallback formatting when required or found values are None."""
    base = {
        "name": "tool",
        "required": ">=1.0",
        "found": "1.0",
        "is_installed": True,
        "is_valid": True,
        "message": "OK",
    }
    mock_check.return_value = [{**base, **dep_overrides}]
    result = runner.invoke(cmd_doctor.doctor)

    assert result.exit_code == 0
    assert expected_required in result.output
    assert expected_found in result.output


@patch.object(cmd_doctor, "check_dependencies", return_value=[])
def test_doctor_command_empty_dependencies(
    mock_check: MagicMock,
    runner: CliRunner,
) -> None:
    """Test doctor command when no dependencies are configured."""
    result = runner.invoke(cmd_doctor.doctor)

    assert result.exit_code == 0
    assert "docbuild System Dependencies" in result.output
    assert "All system dependencies look good!" in result.output


@pytest.mark.parametrize(
    ("dep_results", "expected_exit_code", "expected_snippets", "expected_summary"),
    [
        pytest.param(
            [
                {
                    "name": "jing",
                    "required": ">=20220510",
                    "found": "20220510",
                    "is_installed": True,
                    "is_valid": True,
                    "message": "OK",
                },
                {
                    "name": "rsync",
                    "required": None,
                    "found": "3.4.1",
                    "is_installed": True,
                    "is_valid": True,
                    "message": "OK",
                },
            ],
            0,
            ["jing", "rsync", "✓ OK"],
            "All system dependencies look good!",
            id="multiple_all_ok",
        ),
        pytest.param(
            [
                {
                    "name": "jing",
                    "required": ">=20220510",
                    "found": "20220510",
                    "is_installed": True,
                    "is_valid": True,
                    "message": "OK",
                },
                {
                    "name": "xmllint",
                    "required": ">=2.9.0",
                    "found": "Unknown",
                    "is_installed": True,
                    "is_valid": True,
                    "message": "Warning: Could not determine version",
                },
            ],
            0,
            [
                "jing",
                "xmllint",
                "✓ OK",
                "⚠ Warning: Could not determine version",
            ],
            "All system dependencies look good!",
            id="warning_only_is_non_fatal",
        ),
        pytest.param(
            [
                {
                    "name": "jing",
                    "required": ">=20220510",
                    "found": "20220510",
                    "is_installed": True,
                    "is_valid": True,
                    "message": "OK",
                },
                {
                    "name": "trang",
                    "required": None,
                    "found": None,
                    "is_installed": False,
                    "is_valid": False,
                    "message": "Not found in PATH",
                },
                {
                    "name": "daps",
                    "required": ">=4.0",
                    "found": "3.3.0",
                    "is_installed": True,
                    "is_valid": False,
                    "message": "Version too old",
                },
                {
                    "name": "xmllint",
                    "required": ">=2.9.0",
                    "found": "Unknown",
                    "is_installed": True,
                    "is_valid": True,
                    "message": "Warning: Could not determine version",
                },
                {
                    "name": "rsync",
                    "required": None,
                    "found": "3.4.1",
                    "is_installed": True,
                    "is_valid": True,
                    "message": "OK",
                },
            ],
            1,
            [
                "jing",
                "trang",
                "daps",
                "xmllint",
                "rsync",
                "✓ OK",
                "✗ Missing",
                "✗ Version too old",
                "⚠ Warning: Could not determine version",
            ],
            "Some required system dependencies are missing or outdated.",
            id="mixed_statuses_with_errors",
        ),
    ],
)
@patch.object(cmd_doctor, "check_dependencies")
def test_doctor_command_multiple_dependencies(
    mock_check: MagicMock,
    runner: CliRunner,
    dep_results: list[dict[str, Any]],
    expected_exit_code: int,
    expected_snippets: list[str],
    expected_summary: str,
) -> None:
    """Test doctor displays all rows correctly when multiple dependencies are returned."""
    mock_check.return_value = dep_results
    result = runner.invoke(cmd_doctor.doctor)

    assert result.exit_code == expected_exit_code
    for snippet in expected_snippets:
        assert snippet in result.output
    assert expected_summary in result.output


@patch.object(cmd_doctor, "check_dependencies", return_value=[])
def test_doctor_command_registered_in_cli_group(
    mock_check: MagicMock,
    runner: CliRunner,
) -> None:
    """Test that doctor is registered and executable through the root cli group."""
    result = runner.invoke(cli, ["doctor"])
    assert result.exit_code == 0
    assert "docbuild System Dependencies" in result.output


def test_doctor_command_help(runner: CliRunner) -> None:
    """Test doctor --help displays usage information."""
    result = runner.invoke(cmd_doctor.doctor, ["--help"])
    assert result.exit_code == 0
    assert "Check system dependencies required by docbuild." in result.output
