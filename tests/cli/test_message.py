"""Tests for reusable CLI status messages."""

from io import StringIO
from types import SimpleNamespace
from typing import cast

import pytest
from rich.console import Console

from docbuild.cli.defaults import DEFAULT_APP_CONFIG
from docbuild.cli.message import (
    ERROR,
    INFO,
    INVALID,
    MISSING,
    NO_SYMBOLS_ENV_VAR,
    OK,
    SKIPPED,
    VALID,
    WARNING,
    Message,
    set_symbols_enabled,
    symbols_enabled,
)
from docbuild.cli.theme import DOCBUILD_THEME, ThemeTag
from docbuild.models.config.app import AppConfig

ALL_MESSAGES = (OK, ERROR, WARNING, INFO, VALID, INVALID, SKIPPED, MISSING)


@pytest.fixture(autouse=True)
def reset_symbol_setting():
    """Reset the shared application-config default around each test."""
    set_symbols_enabled(True)
    yield
    set_symbols_enabled(True)


def test_message_str_returns_plain_label():
    """Verify str() returns only the label, without styling or symbols."""
    assert str(VALID) == "Valid"
    assert str(OK) == "OK"


def test_message_render_includes_symbol_by_default(monkeypatch):
    """Verify render() includes the symbol and semantic style by default."""
    monkeypatch.delenv(NO_SYMBOLS_ENV_VAR, raising=False)

    text = VALID.render()

    assert text.plain == "✓ Valid"
    assert text.style == ThemeTag.SUCCESS.value


def test_message_render_can_omit_symbols(monkeypatch):
    """Verify render(symbols=False) keeps the label and drops the symbol."""
    monkeypatch.delenv(NO_SYMBOLS_ENV_VAR, raising=False)

    text = WARNING.render(symbols=False)

    assert text.plain == "Warning"
    assert text.style == ThemeTag.WARNING.value


def test_message_render_keeps_symbol_for_utf8_console(monkeypatch):
    """Verify render() keeps the symbol when the console encoding supports it."""
    monkeypatch.delenv(NO_SYMBOLS_ENV_VAR, raising=False)
    console = cast(Console, SimpleNamespace(encoding="utf-8"))

    assert VALID.render(console=console).plain == "✓ Valid"


def test_message_render_drops_symbol_for_ascii_console(monkeypatch):
    """Verify render() drops an unencodable symbol but keeps the label."""
    monkeypatch.delenv(NO_SYMBOLS_ENV_VAR, raising=False)
    console = cast(Console, SimpleNamespace(encoding="ascii"))

    assert VALID.render(console=console).plain == "Valid"


def test_message_render_respects_shared_opt_out(monkeypatch):
    """Verify the shared environment opt-out disables symbols."""
    monkeypatch.setenv(NO_SYMBOLS_ENV_VAR, "1")

    assert symbols_enabled() is False
    assert VALID.render().plain == "Valid"


def test_explicit_symbols_override_shared_opt_out(monkeypatch):
    """Verify an explicit symbols value overrides the shared opt-out."""
    monkeypatch.setenv(NO_SYMBOLS_ENV_VAR, "1")

    assert VALID.render(symbols=True).plain == "✓ Valid"


def test_app_config_disables_symbols():
    """Verify the application-config default disables symbols."""
    set_symbols_enabled(False)

    assert symbols_enabled() is False
    assert VALID.render().plain == "Valid"


def test_env_var_overrides_app_config(monkeypatch):
    """Verify the environment variable takes precedence over app config."""
    set_symbols_enabled(False)
    monkeypatch.setenv(NO_SYMBOLS_ENV_VAR, "0")

    assert symbols_enabled() is True
    assert VALID.render().plain == "✓ Valid"


def test_appconfig_symbols_setting():
    """Verify AppConfig exposes the symbols setting with a true default."""
    assert AppConfig.from_dict({}).symbols is True
    assert AppConfig.from_dict({"symbols": False}).symbols is False


def test_default_app_config_defines_symbols_default():
    """Verify the built-in application defaults enable symbols."""
    assert DEFAULT_APP_CONFIG["symbols"] is True


def test_apply_message_settings_uses_app_config():
    """Verify the CLI wiring applies the application-config symbols value."""
    from docbuild.cli.cmd_cli import apply_message_settings
    from docbuild.cli.context import DocBuildContext

    context = DocBuildContext()
    context.appconfig = AppConfig.from_dict({"symbols": False})

    apply_message_settings(context)

    assert symbols_enabled() is False


def test_apply_message_settings_ignores_missing_config():
    """Verify the CLI wiring keeps defaults when no app config is loaded."""
    from docbuild.cli.cmd_cli import apply_message_settings

    apply_message_settings(None)

    assert symbols_enabled() is True


@pytest.mark.parametrize("value", ["", "0", "false", "no", "off"])
def test_symbols_enabled_values(monkeypatch, value):
    """Verify falsy opt-out values keep symbols enabled."""
    monkeypatch.setenv(NO_SYMBOLS_ENV_VAR, value)

    assert symbols_enabled() is True


def test_message_rich_console_rendering(monkeypatch):
    """Verify Rich renders a Message inline inside console.print()."""
    monkeypatch.delenv(NO_SYMBOLS_ENV_VAR, raising=False)
    monkeypatch.setattr("docbuild.cli.message._stdout_encoding", lambda: "utf-8")
    output = StringIO()
    console = Console(file=output, theme=DOCBUILD_THEME, width=80)

    console.print("Application configuration:", VALID)

    assert "Application configuration: ✓ Valid" in output.getvalue()


def test_message_rich_render_drops_symbol_for_ascii_stdout(monkeypatch):
    """Verify Rich rendering drops symbols the standard output cannot encode."""
    monkeypatch.delenv(NO_SYMBOLS_ENV_VAR, raising=False)
    monkeypatch.setattr("docbuild.cli.message._stdout_encoding", lambda: "ascii")
    output = StringIO()
    console = Console(file=output, theme=DOCBUILD_THEME, width=80)

    console.print("Application configuration:", VALID)

    assert "Application configuration: Valid" in output.getvalue()


def test_message_constants_use_theme_tags():
    """Verify all predefined messages have a label and a valid theme tag."""
    for message in ALL_MESSAGES:
        assert isinstance(message, Message)
        assert message.label
        assert isinstance(message.style, ThemeTag)
