"""Tests for reusable CLI status messages."""

from contextvars import Context
from io import BytesIO, StringIO, TextIOWrapper
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
    """Reset the application-config default around each test."""
    set_symbols_enabled(True)
    yield
    set_symbols_enabled(True)


@pytest.mark.parametrize("message", ALL_MESSAGES)
def test_message_str_returns_plain_label(message):
    """Verify str() returns only the label, without styling or symbols."""
    assert str(message) == message.label


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


def test_symbol_setting_is_context_local(monkeypatch):
    """Verify the application-config default is isolated per context."""
    monkeypatch.delenv(NO_SYMBOLS_ENV_VAR, raising=False)
    set_symbols_enabled(False)

    assert symbols_enabled() is False
    assert Context().run(symbols_enabled) is True


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
    """Verify rendered messages stay inline when printed with a prefix."""
    monkeypatch.delenv(NO_SYMBOLS_ENV_VAR, raising=False)
    output = StringIO()
    console = Console(file=output, theme=DOCBUILD_THEME, width=80)

    console.print("Application configuration:", VALID.render(console=console))

    assert "Application configuration: ✓ Valid" in output.getvalue()


@pytest.mark.parametrize(
    ("encoding", "expected"),
    [
        pytest.param("ascii", b"Valid\n", id="ascii"),
        pytest.param("utf-8", "✓ Valid\n".encode(), id="utf-8"),
    ],
)
def test_message_rich_console_uses_destination_encoding(
    monkeypatch, encoding, expected
):
    """Verify Rich rendering uses the destination console encoding."""
    monkeypatch.delenv(NO_SYMBOLS_ENV_VAR, raising=False)
    buffer = BytesIO()
    stream = TextIOWrapper(buffer, encoding=encoding, newline="")
    console = Console(file=stream, theme=DOCBUILD_THEME, width=80)

    console.print(VALID)
    stream.flush()

    assert buffer.getvalue() == expected


def test_message_constants_use_theme_tags():
    """Verify all predefined messages have a label and a valid theme tag."""
    for message in ALL_MESSAGES:
        assert isinstance(message, Message)
        assert message.label
        assert isinstance(message.style, ThemeTag)
