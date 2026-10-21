"""Tests for system dependency validation and version checking."""

import dataclasses
import logging
from pathlib import Path
import subprocess
from unittest.mock import MagicMock, patch

from click.testing import CliRunner
import pytest

from docbuild.constants import SYSTEM_DEPENDENCIES, DependencySpec
from docbuild.utils import sysdeps


def test_dependency_spec_defaults_and_immutability() -> None:
    """DependencySpec sets expected defaults and is immutable."""
    spec = DependencySpec()
    assert spec.required is None
    assert spec.args == ("--version",)

    custom = DependencySpec(required=">=1.0.0", args=("-v",))
    assert custom.required == ">=1.0.0"
    assert custom.args == ("-v",)

    with pytest.raises(dataclasses.FrozenInstanceError):
        spec.required = ">=2.0.0"  # type: ignore[misc]


def test_system_dependencies_spec_definitions() -> None:
    """SYSTEM_DEPENDENCIES contains DependencySpec instances with expected configurations."""
    for name, spec in SYSTEM_DEPENDENCIES.items():
        assert isinstance(spec, DependencySpec), f"{name} is not a DependencySpec"

    # Jing and Trang should specify empty args to avoid hanging/invalid option error
    assert SYSTEM_DEPENDENCIES["jing"].args == ()
    assert SYSTEM_DEPENDENCIES["trang"].args == ()
    assert SYSTEM_DEPENDENCIES["daps"].args == ("--version",)


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


def test_get_binary_version_returns_none_on_subprocess_error() -> None:
    """A SubprocessError (e.g. timeout) yields None instead of raising."""
    with patch.object(
        subprocess,
        "run",
        side_effect=subprocess.TimeoutExpired(cmd=["tool"], timeout=5.0),
    ):
        assert sysdeps.get_binary_version("hanging-tool") is None


def test_get_binary_version_logs_debug_on_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A subprocess failure logs a debug message."""
    with (
        patch.object(subprocess, "run", side_effect=OSError("binary crashed")),
        caplog.at_level(logging.DEBUG, logger=sysdeps.__name__),
    ):
        result = sysdeps.get_binary_version("broken-tool")
        assert result is None
        assert (
            "Failed to execute 'broken-tool' to retrieve version: binary crashed"
            in caplog.text
        )


def test_get_binary_version_custom_args() -> None:
    """Custom CLI arguments are forwarded to subprocess.run."""
    mock_result = MagicMock()
    mock_result.stdout = "tool version 1.2.3\n"
    mock_result.stderr = ""

    with patch.object(subprocess, "run", return_value=mock_result) as mock_run:
        assert sysdeps.get_binary_version("tool", args=("-V",)) == "1.2.3"
        mock_run.assert_called_once_with(
            ["tool", "-V"],
            capture_output=True,
            text=True,
            errors="replace",
            check=False,
            stdin=subprocess.DEVNULL,
            timeout=5.0,
        )


def test_get_binary_version_custom_timeout() -> None:
    """Custom timeout is forwarded to subprocess.run."""
    mock_result = MagicMock()
    mock_result.stdout = "1.0.0"
    mock_result.stderr = ""

    with patch.object(subprocess, "run", return_value=mock_result) as mock_run:
        assert sysdeps.get_binary_version("tool", timeout=12.5) == "1.0.0"
        mock_run.assert_called_once_with(
            ["tool", "--version"],
            capture_output=True,
            text=True,
            errors="replace",
            check=False,
            stdin=subprocess.DEVNULL,
            timeout=12.5,
        )


def test_check_dependencies_passes_spec_args() -> None:
    """check_dependencies passes DependencySpec.args to get_binary_version."""
    with (
        patch.object(sysdeps.shutil, "which", return_value="/usr/bin/jing"),
        patch.object(
            sysdeps, "get_binary_version", return_value="20220510"
        ) as mock_gbv,
        patch.object(
            sysdeps,
            "SYSTEM_DEPENDENCIES",
            {"jing": DependencySpec(required=">=20220510", args=())},
        ),
    ):
        results = sysdeps.check_dependencies()

    mock_gbv.assert_called_once_with("jing", args=())
    assert results[0]["is_installed"] is True
    assert results[0]["is_valid"] is True
    assert results[0]["found"] == "20220510"


def test_check_dependencies_supports_legacy_string_spec() -> None:
    """check_dependencies converts raw string requirements into DependencySpec objects."""
    with (
        patch.object(sysdeps.shutil, "which", return_value="/usr/bin/legacy"),
        patch.object(sysdeps, "get_binary_version", return_value="2.0.0") as mock_gbv,
        patch.object(
            sysdeps,
            "SYSTEM_DEPENDENCIES",
            {"legacy": ">=1.0.0"},
        ),
    ):
        results = sysdeps.check_dependencies()

    mock_gbv.assert_called_once_with("legacy", args=("--version",))
    assert len(results) == 1
    assert results[0]["name"] == "legacy"
    assert results[0]["required"] == ">=1.0.0"
    assert results[0]["is_installed"] is True
    assert results[0]["is_valid"] is True


def test_coerce_semver_pure_integer() -> None:
    """A plain integer version is treated as a single major version."""
    assert sysdeps.coerce_semver("4") == sysdeps.semver.Version(4)


def test_coerce_semver_pads_incomplete_parts() -> None:
    """Short versions are zero-padded to strict SemVer."""
    assert str(sysdeps.coerce_semver("3.4")) == "3.4.0"


def test_coerce_semver_truncates_extra_parts() -> None:
    """Extra version parts are dropped to keep three segments."""
    assert str(sysdeps.coerce_semver("1.2.3.4")) == "1.2.3"


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


def test_requires_system_tools_defaults_to_all_tools(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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

        monkeypatch.chdir(tmp_path)
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
