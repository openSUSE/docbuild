"""Tests for the docbuild doctor command."""

from unittest.mock import patch

from click.testing import CliRunner

from docbuild.cli import cmd_doctor


def test_doctor_command_success_no_errors():
    """Test that doctor exits with 0 when all dependencies are met."""
    runner = CliRunner()

    # Mock the checker engine using patch.object for better IDE refactoring support
    with patch.object(cmd_doctor, "check_dependencies") as mock_check:
        mock_check.return_value = [
            {
                "name": "mock-tool",
                "required": ">=1.0",
                "found": "2.0",
                "is_installed": True,
                "is_valid": True,
                "message": "OK",
            }
        ]
        result = runner.invoke(cmd_doctor.doctor)

        assert result.exit_code == 0
        assert "mock-tool" in result.output
        assert "All system dependencies look good!" in result.output


def test_doctor_command_fails_on_missing_tool():
    """Test that doctor exits with 1 when a dependency is missing."""
    runner = CliRunner()

    with patch.object(cmd_doctor, "check_dependencies") as mock_check:
        mock_check.return_value = [
            {
                "name": "missing-tool",
                "required": ">=1.0",
                "found": None,
                "is_installed": False,
                "is_valid": False,
                "message": "Not found in PATH",
            }
        ]
        result = runner.invoke(cmd_doctor.doctor)

        assert result.exit_code == 1
        assert "missing-tool" in result.output
        assert "Missing" in result.output
        assert "missing or outdated" in result.output
