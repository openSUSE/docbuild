"""Tests for system dependency validation and version checking."""

import subprocess
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from docbuild.utils import sysdeps


def test_get_binary_version_parses_stdout() -> None:
    """Version string is extracted from stdout output."""
    mock_result = MagicMock()
    mock_result.stdout = "jing version 20220510 (xml syntax)\n"
    mock_result.stderr = ""

    with patch.object(subprocess, "run", return_value=mock_result):
        assert sysdeps.get_binary_version("jing") == "20220510"


def test_get_binary_version_falls_back_to_stderr() -> None:
    """Version string is extracted from stderr when stdout is empty."""
    mock_result = MagicMock()
    mock_result.stdout = ""
    mock_result.stderr = "daps version 4.0.0\n"

    with patch.object(subprocess, "run", return_value=mock_result):
        assert sysdeps.get_binary_version("daps") == "4.0.0"


def test_get_binary_version_returns_none_without_match() -> None:
    """No numeric version in the output yields None."""
    mock_result = MagicMock()
    mock_result.stdout = "not a version here\n"
    mock_result.stderr = ""

    with patch.object(subprocess, "run", return_value=mock_result):
        assert sysdeps.get_binary_version("foo") is None


def test_get_binary_version_returns_none_on_error() -> None:
    """A subprocess failure yields None instead of raising."""
    with patch.object(subprocess, "run", side_effect=OSError("missing")):
        assert sysdeps.get_binary_version("missing-tool") is None


def test_coerce_semver_pure_integer() -> None:
    """A plain integer version is treated as a single major version."""
    assert sysdeps._coerce_semver("4") == sysdeps.semver.Version(4)


def test_coerce_semver_pads_incomplete_parts() -> None:
    """Short versions are zero-padded to strict SemVer."""
    assert str(sysdeps._coerce_semver("3.4")) == "3.4.0"


def test_coerce_semver_truncates_extra_parts() -> None:
    """Extra version parts are dropped to keep three segments."""
    assert str(sysdeps._coerce_semver("1.2.3.4")) == "1.2.3"


def test_check_dependencies_returns_missing_when_not_installed() -> None:
    """A tool missing from PATH is reported as not installed."""
    with (
        patch.object(sysdeps.shutil, "which", return_value=None),
        patch.object(sysdeps, "get_binary_version"),
    ):
        results = sysdeps.check_dependencies()

    jing = next(r for r in results if r["name"] == "jing")
    assert jing["is_installed"] is False
    assert jing["is_valid"] is False
    assert jing["message"] == "Not found in PATH"
    assert jing["found"] is None


def test_check_dependencies_any_version_is_valid() -> None:
    """A tool without a version requirement is always valid."""
    with (
        patch.object(sysdeps.shutil, "which", return_value="/usr/bin/xmllint"),
        patch.object(sysdeps, "get_binary_version", return_value="2.10.3"),
    ):
        results = sysdeps.check_dependencies()

    xmllint = next(r for r in results if r["name"] == "xmllint")
    assert xmllint["is_installed"] is True
    assert xmllint["is_valid"] is True
    assert xmllint["message"] == "OK"
    assert xmllint["required"] == "Any"


def test_check_dependencies_unparseable_requirement_warns() -> None:
    """An unparseable requirement reports OK with a warning message."""
    with (
        patch.object(sysdeps.shutil, "which", return_value="/usr/bin/foo"),
        patch.object(sysdeps, "get_binary_version", return_value="1.0"),
        patch.object(sysdeps, "SYSTEM_DEPENDENCIES", {"foo": "???"}),
    ):
        results = sysdeps.check_dependencies()

    foo = results[0]
    assert foo["is_installed"] is True
    assert foo["is_valid"] is True
    assert foo["message"] == "Cannot parse requirement: ???"


def test_check_dependencies_unknown_version_warns() -> None:
    """A tool with an unknown version reports a warning but is valid."""
    with (
        patch.object(sysdeps.shutil, "which", return_value="/usr/bin/jing"),
        patch.object(sysdeps, "get_binary_version", return_value=None),
        patch.object(sysdeps, "SYSTEM_DEPENDENCIES", {"jing": ">=20220510"}),
    ):
        results = sysdeps.check_dependencies()

    jing = results[0]
    assert jing["is_installed"] is True
    assert jing["is_valid"] is True
    assert jing["found"] == "Unknown"
    assert jing["message"] == "Warning: Could not determine version"


def test_check_dependencies_valid_version() -> None:
    """A satisfying version is reported as OK."""
    with (
        patch.object(sysdeps.shutil, "which", return_value="/usr/bin/jing"),
        patch.object(sysdeps, "get_binary_version", return_value="20220510"),
        patch.object(sysdeps, "SYSTEM_DEPENDENCIES", {"jing": ">=20220510"}),
    ):
        results = sysdeps.check_dependencies()

    jing = results[0]
    assert jing["is_installed"] is True
    assert jing["is_valid"] is True
    assert jing["message"] == "OK"
    assert jing["found"] == "20220510"


def test_check_dependencies_version_too_old() -> None:
    """A version below the requirement is reported as invalid."""
    with (
        patch.object(sysdeps.shutil, "which", return_value="/usr/bin/jing"),
        patch.object(sysdeps, "get_binary_version", return_value="1.0"),
        patch.object(sysdeps, "SYSTEM_DEPENDENCIES", {"jing": ">=20220510"}),
    ):
        results = sysdeps.check_dependencies()

    jing = results[0]
    assert jing["is_installed"] is True
    assert jing["is_valid"] is False
    assert jing["message"] == "Version too old"


def test_check_dependencies_comparison_failure_warns() -> None:
    """A version that cannot be compared reports a warning but is valid."""
    with (
        patch.object(sysdeps.shutil, "which", return_value="/usr/bin/jing"),
        patch.object(sysdeps, "get_binary_version", return_value="!!!"),
        patch.object(sysdeps, "SYSTEM_DEPENDENCIES", {"jing": ">=20220510"}),
    ):
        results = sysdeps.check_dependencies()

    jing = results[0]
    assert jing["is_installed"] is True
    assert jing["is_valid"] is True
    assert jing["message"] == "Warning: Version comparison failed"


def test_requires_system_tools_defaults_to_all_tools() -> None:
    """Without arguments, all system dependencies are required."""
    statuses = [
        {
            "name": "jing",
            "required": ">=20220510",
            "found": None,
            "is_installed": False,
            "is_valid": False,
            "message": "Not found in PATH",
        }
    ]
    with (
        patch.object(sysdeps, "check_dependencies", return_value=statuses),
        patch.object(sysdeps.click, "get_current_context") as mock_ctx,
    ):
        context = mock_ctx.return_value

        @sysdeps.requires_system_tools()
        def command():
            pass

        with CliRunner().isolated_filesystem():
            command()

        context.exit.assert_called_once_with(1)


def test_requires_system_tools_explicit_tools_ignores_others() -> None:
    """Only the listed tools are considered when tools are passed."""
    statuses = [
        {
            "name": "xmllint",
            "required": None,
            "found": "2.10.3",
            "is_installed": True,
            "is_valid": True,
            "message": "OK",
        },
        {
            "name": "daps",
            "required": ">=4",
            "found": None,
            "is_installed": False,
            "is_valid": False,
            "message": "Not found in PATH",
        },
    ]
    with patch.object(
        sysdeps, "check_dependencies", return_value=statuses
    ) as mock_check:
        called = []

        @sysdeps.requires_system_tools(["xmllint"])
        def command():
            called.append(True)

        command()

    mock_check.assert_called_once()
    assert called == [True]


def test_requires_system_tools_missing_tool_exits() -> None:
    """A missing required tool aborts the command with exit code 1."""
    statuses = [
        {
            "name": "daps",
            "required": ">=4",
            "found": None,
            "is_installed": False,
            "is_valid": False,
            "message": "Not found in PATH",
        }
    ]
    runner = CliRunner()
    with (
        patch.object(sysdeps, "check_dependencies", return_value=statuses),
        patch.object(sysdeps.click, "secho") as mock_secho,
    ):

        @sysdeps.click.command()
        @sysdeps.requires_system_tools(["daps"])
        def command():
            return "should not run"

        result = runner.invoke(command, [])

    assert result.exit_code == 1
    mock_secho.assert_called_once()
    assert "daps" in mock_secho.call_args.args[0]


def test_requires_system_tools_outdated_tool_exits() -> None:
    """An outdated required tool aborts the command with exit code 1."""
    statuses = [
        {
            "name": "jing",
            "required": ">=20220510",
            "found": "1.0",
            "is_installed": True,
            "is_valid": False,
            "message": "Version too old",
        }
    ]
    runner = CliRunner()
    with (
        patch.object(sysdeps, "check_dependencies", return_value=statuses),
        patch.object(sysdeps.click, "secho") as mock_secho,
    ):

        @sysdeps.click.command()
        @sysdeps.requires_system_tools(["jing"])
        def command():
            return "should not run"

        result = runner.invoke(command, [])

    assert result.exit_code == 1
    assert "jing" in mock_secho.call_args.args[0]


def test_requires_system_tools_all_ok_calls_command() -> None:
    """When all tools are valid, the wrapped command runs."""
    statuses = [
        {
            "name": "daps",
            "required": ">=4",
            "found": "4.2",
            "is_installed": True,
            "is_valid": True,
            "message": "OK",
        }
    ]
    runner = CliRunner()
    with patch.object(sysdeps, "check_dependencies", return_value=statuses):

        @sysdeps.click.command()
        @sysdeps.requires_system_tools(["daps"])
        def command():
            sysdeps.click.echo("ran")

        result = runner.invoke(command, [])

    assert result.exit_code == 0
    assert result.output == "ran\n"
