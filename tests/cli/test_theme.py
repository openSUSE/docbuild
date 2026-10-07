"""Tests for Rich theme configuration and integration."""

from collections import UserDict
from unittest.mock import MagicMock

from pydantic import ValidationError
import pytest
from rich.console import Console
from rich.theme import Theme

from docbuild.cli.cmd_cli import CONSOLE, apply_theme_overrides
from docbuild.cli.context import DocBuildContext
from docbuild.cli.defaults import DEFAULT_APP_CONFIG
from docbuild.cli.theme import (
    DARK_THEME_STYLES,
    DEFAULT_STYLES,
    DOCBUILD_THEME,
    LIGHT_THEME_STYLES,
    THEME_STYLES,
    ModeStyle,
    ThemeTag,
    get_theme,
)
from docbuild.models.config.app import AppConfig


def test_theme_tags_enum():
    """Verify ThemeTag enum members match expected semantic tokens."""
    expected = {"header", "error", "warning", "info", "success", "hint", "muted", "lang", "product", "docset"}
    assert {tag.value for tag in ThemeTag} == expected


def test_default_styles_keys():
    """Verify all agreed-upon semantic style keys are present in default styles."""
    expected_keys = {
        ThemeTag.HEADER,
        ThemeTag.ERROR,
        ThemeTag.WARNING,
        ThemeTag.INFO,
        ThemeTag.SUCCESS,
        ThemeTag.HINT,
        ThemeTag.MUTED,
        ThemeTag.LANG,
        ThemeTag.PRODUCT,
        ThemeTag.DOCSET,
    }
    assert expected_keys == set(DEFAULT_STYLES.keys())
    assert expected_keys == set(DARK_THEME_STYLES.keys())
    assert expected_keys == set(LIGHT_THEME_STYLES.keys())
    assert expected_keys == set(THEME_STYLES.keys())


def test_mode_style_dataclass():
    """Verify ModeStyle dataclass holds dark and light attributes immutably."""
    ms = ModeStyle(dark="bold cyan", light="bold blue")
    assert ms.dark == "bold cyan"
    assert ms.light == "bold blue"

    with pytest.raises(AttributeError):
        ms.dark = "other"  # type: ignore[misc]

    # Verify subscripting is forbidden (not a tuple)
    with pytest.raises(TypeError):
        _ = ms[0]  # type: ignore[index]



def test_default_app_config_defines_theme_defaults():
    """Verify DEFAULT_APP_CONFIG defines a theme entry."""
    assert "theme" in DEFAULT_APP_CONFIG
    assert DEFAULT_APP_CONFIG["theme"] == {}


def test_get_theme_defaults():
    """Verify get_theme returns a Theme instance with default styles."""
    theme = get_theme()
    assert isinstance(theme, Theme)
    for key in DEFAULT_STYLES:
        assert key in theme.styles


def test_get_theme_presets():
    """Verify get_theme creates appropriate styles for dark and light presets."""
    dark_theme = get_theme(preset="dark")
    assert dark_theme.styles["header"] == Console(theme=dark_theme).get_style(DARK_THEME_STYLES[ThemeTag.HEADER])

    light_theme = get_theme(preset="light")
    assert light_theme.styles["header"] == Console(theme=light_theme).get_style(LIGHT_THEME_STYLES[ThemeTag.HEADER])


def test_get_theme_invalid_preset():
    """Verify get_theme raises ValueError on unknown presets."""
    with pytest.raises(ValueError, match="Invalid theme preset 'invalid'"):
        get_theme(preset="invalid")


def test_get_theme_invalid_style_syntax(capsys):
    """Verify get_theme catches StyleSyntaxError, prints to stderr, and exits with 1."""
    with pytest.raises(SystemExit) as exc_info:
        get_theme({ThemeTag.WARNING: ":warn:"})

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Error: unable to parse ':warn:' as color" in captured.err


def test_get_theme_overrides():
    """Verify get_theme overrides default styles and adds new ones."""
    custom = {"error": "magenta", "custom_tag": "bold yellow"}
    theme = get_theme(custom)
    assert isinstance(theme, Theme)
    assert "custom_tag" in theme.styles
    console = Console(theme=theme)
    style = console.get_style("error")
    assert style.color and style.color.name == "magenta"


def test_get_theme_custom_mapping():
    """Verify get_theme works with non-dict Mapping implementations."""
    custom_mapping = UserDict({"warning": "bold magenta"})
    theme = get_theme(custom_mapping)
    assert isinstance(theme, Theme)
    console = Console(theme=theme)
    style = console.get_style("warning")
    assert style.color and style.color.name == "magenta"


def test_docbuild_theme_instance():
    """Verify DOCBUILD_THEME is a valid Theme instance containing default styles."""
    assert isinstance(DOCBUILD_THEME, Theme)
    for key in DEFAULT_STYLES:
        assert key in DOCBUILD_THEME.styles


def test_appconfig_theme_defaults():
    """Verify AppConfig defaults to a populated dictionary with standard styles."""
    config = AppConfig.from_dict({})
    assert isinstance(config.theme, dict)
    assert config.theme[ThemeTag.ERROR] == DARK_THEME_STYLES[ThemeTag.ERROR]
    assert config.theme[ThemeTag.HEADER] == DARK_THEME_STYLES[ThemeTag.HEADER]
    assert config.theme[ThemeTag.SUCCESS] == DARK_THEME_STYLES[ThemeTag.SUCCESS]


def test_appconfig_theme_preset_selection():
    """Verify AppConfig supports selecting 'dark' and 'light' theme presets."""
    light_config = AppConfig.from_dict({"theme": {"preset": "light"}})
    assert light_config.theme[ThemeTag.HEADER] == LIGHT_THEME_STYLES[ThemeTag.HEADER]
    assert light_config.theme[ThemeTag.WARNING] == LIGHT_THEME_STYLES[ThemeTag.WARNING]

    dark_config = AppConfig.from_dict({"theme": {"preset": "dark"}})
    assert dark_config.theme[ThemeTag.HEADER] == DARK_THEME_STYLES[ThemeTag.HEADER]
    assert dark_config.theme[ThemeTag.WARNING] == DARK_THEME_STYLES[ThemeTag.WARNING]


def test_appconfig_theme_invalid_preset():
    """Verify AppConfig rejects unsupported theme presets."""
    with pytest.raises(ValidationError, match="Invalid theme preset 'neon'"):
        AppConfig.from_dict({"theme": {"preset": "neon"}})


def test_appconfig_theme_custom_valid():
    """Verify AppConfig accepts partial theme overrides and retains other defaults."""
    valid_theme = {"error": "bold magenta"}
    config = AppConfig.from_dict({"theme": valid_theme})
    assert config.theme[ThemeTag.ERROR] == "bold magenta"
    # Other defaults remain intact
    assert config.theme[ThemeTag.SUCCESS] == DARK_THEME_STYLES[ThemeTag.SUCCESS]


def test_appconfig_theme_invalid_tag_name():
    """Verify AppConfig rejects unknown theme tag names not in ThemeTag enum."""
    invalid_theme = {"not_a_valid_tag": "bold red"}
    with pytest.raises(ValidationError):
        AppConfig.from_dict({"theme": invalid_theme})


def test_appconfig_theme_invalid_syntax():
    """Verify AppConfig rejects invalid Rich style syntax."""
    invalid_theme = {"error": "invalid-color-that-does-not-exist"}
    with pytest.raises(ValidationError, match="Invalid Rich style syntax"):
        AppConfig.from_dict({"theme": invalid_theme})


def test_appconfig_theme_non_dict():
    """Verify AppConfig rejects non-dictionary theme inputs."""
    with pytest.raises(ValidationError):
        AppConfig.model_validate({"theme": "not-a-dict"})


def test_appconfig_theme_structured_table():
    """Verify AppConfig supports structured style tables in addition to strings."""
    structured = {
        "error": {"color": "red", "bold": True, "bgcolor": "black"},
        "warning": {"color": "yellow", "italic": True},
    }
    config = AppConfig.from_dict({"theme": structured})
    assert config.theme[ThemeTag.ERROR] == "bold red on black"
    assert config.theme[ThemeTag.WARNING] == "italic yellow"
    assert config.theme[ThemeTag.SUCCESS] == DARK_THEME_STYLES[ThemeTag.SUCCESS]


def test_appconfig_theme_structured_table_invalid():
    """Verify AppConfig rejects invalid keys/colors in structured style tables."""
    structured = {"error": {"color": "not-a-color"}}
    with pytest.raises(ValidationError, match="Invalid style table for 'error'"):
        AppConfig.from_dict({"theme": structured})


def test_apply_theme_overrides_pushes_theme():
    """Verify apply_theme_overrides pushes theme overrides onto CONSOLE."""
    # Ensure any residual pushed themes on CONSOLE are reset
    while len(CONSOLE._theme_stack._entries) > 1:
        CONSOLE.pop_theme()

    context = DocBuildContext()
    context.appconfig = AppConfig.from_dict({"theme": {"info": "magenta"}})

    # Record current style
    initial_style = CONSOLE.get_style("info")

    try:
        apply_theme_overrides(context)
        style = CONSOLE.get_style("info")
        assert style.color and style.color.name == "magenta"

        # Calling again with default config resets previously pushed overrides
        context_default = DocBuildContext()
        context_default.appconfig = AppConfig.from_dict({})
        apply_theme_overrides(context_default)
        assert CONSOLE.get_style("info") == initial_style
    finally:
        # Clean up theme stack
        while len(CONSOLE._theme_stack._entries) > 1:
            CONSOLE.pop_theme()

    assert CONSOLE.get_style("info") == initial_style


def test_apply_theme_overrides_noop_when_mock_or_none():
    """Verify apply_theme_overrides does not crash when theme is non-dict mock or None."""
    # Verify passing None causes no error
    apply_theme_overrides(None)

    # Verify passing context with default theme causes no theme push
    context_default = DocBuildContext()
    context_default.appconfig = AppConfig.from_dict({})
    initial_stack_len = len(CONSOLE._theme_stack._entries)
    apply_theme_overrides(context_default)
    assert len(CONSOLE._theme_stack._entries) == initial_stack_len

    # Verify mock context where theme is not a dict causes no error
    mock_context = MagicMock()
    mock_context.appconfig.theme = "not-a-dict"
    apply_theme_overrides(mock_context)


def test_fallback_console_theme_in_errors(capsys):
    """Verify format_pydantic_error and format_toml_error fall back to themed console_err."""
    import tomllib

    from pydantic import BaseModel

    from docbuild.cli.console import console_err
    from docbuild.utils.errors import format_pydantic_error, format_toml_error

    assert console_err._theme_stack._entries[-1]["error"] == DOCBUILD_THEME.styles["error"]

    class DummyModel(BaseModel):
        num: int

    try:
        DummyModel(num="not-a-number")  # type: ignore[arg-type]
    except ValidationError as err:
        format_pydantic_error(err, DummyModel, "dummy.toml", console=None)

    captured = capsys.readouterr()
    assert "Validation error" in captured.err

    try:
        tomllib.loads("bad = True")
    except tomllib.TOMLDecodeError as err:
        format_toml_error(err, "dummy.toml", console=None)

    captured2 = capsys.readouterr()
    assert "Syntax error" in captured2.err
