"""Tests for the 'config validate' CLI command."""

from pathlib import Path
from types import SimpleNamespace

from click.testing import CliRunner
import pytest

from docbuild.cli.cmd_config.validate import validate


def make_context(**overrides) -> SimpleNamespace:
    """Create a minimal context object for the validate command."""
    values = {
        "appconfig": object(),
        "appconfigfiles": [Path("app.toml")],
        "envconfig": object(),
        "envconfigfiles": [Path("env.toml")],
        "envconfig_from_defaults": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_validate_lists_all_config_files():
    """Test that both app and env config files are listed."""
    result = CliRunner().invoke(validate, obj=make_context())

    assert result.exit_code == 0
    assert "Application Configuration" in result.output
    assert "app.toml" in result.output
    assert "Environment Configuration" in result.output
    assert "env.toml" in result.output
    assert "Configuration is valid" in result.output


def test_validate_without_app_and_env_config():
    """Test that missing configs skip their sections but still succeed."""
    ctx = make_context(appconfig=None, envconfig=None)
    result = CliRunner().invoke(validate, obj=ctx)

    assert result.exit_code == 0
    assert "Application Configuration" not in result.output
    assert "Environment Configuration" not in result.output
    assert "Configuration is valid" in result.output


@pytest.mark.parametrize(
    ("from_defaults", "expected"),
    [(True, True), (False, False)],
)
def test_validate_env_config_without_files(from_defaults: bool, expected: bool):
    """Test the internal-defaults hint when no env config files are given."""
    ctx = make_context(envconfigfiles=[], envconfig_from_defaults=from_defaults)
    result = CliRunner().invoke(validate, obj=ctx)

    assert result.exit_code == 0
    assert "Environment Configuration" in result.output
    assert ("Using internal defaults" in result.output) is expected


def test_validate_app_config_files_none():
    """Test that a missing appconfigfiles list is handled gracefully."""
    ctx = make_context(appconfigfiles=None)
    result = CliRunner().invoke(validate, obj=ctx)

    assert result.exit_code == 0
    assert "app.toml" not in result.output
