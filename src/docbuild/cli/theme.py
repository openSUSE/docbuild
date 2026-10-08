"""Rich theme definitions and styling tokens for docbuild."""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
import sys

from rich.errors import StyleSyntaxError
from rich.theme import Theme


class ThemeTag(StrEnum):
    """Semantic style tags used across docbuild CLI."""

    HEADER = "header"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    SUCCESS = "success"
    HINT = "hint"
    MUTED = "muted"
    #
    LANG = "lang"
    PRODUCT = "product"
    DOCSET = "docset"


@dataclass(frozen=True, slots=True)
class ModeStyle:
    """Style definitions for dark and light terminal backgrounds.

    See also https://rich.readthedocs.io/en/stable/appendix/colors.html
    """

    dark: str
    """Style string for dark terminal backgrounds."""

    light: str
    """Style string for light terminal backgrounds."""


# For available colors, see:
# https://rich.readthedocs.io/en/stable/appendix/colors.html
THEME_STYLES: dict[ThemeTag, ModeStyle] = {
    ThemeTag.HEADER: ModeStyle(dark="bold sky_blue2", light="bold blue"),
    ThemeTag.ERROR: ModeStyle(dark="bold red", light="bold red"),
    ThemeTag.WARNING: ModeStyle(dark="bold yellow", light="bold dark_goldenrod"),
    ThemeTag.INFO: ModeStyle(dark="bright_blue", light="bold dark_cyan"),
    ThemeTag.SUCCESS: ModeStyle(dark="bold green", light="bold dark_green"),
    ThemeTag.HINT: ModeStyle(dark="dim italic cyan", light="italic dark_cyan"),
    ThemeTag.MUTED: ModeStyle(dark="dim white", light="dim black"),
    #
    ThemeTag.LANG: ModeStyle(dark="orchid", light="orchid"),
    ThemeTag.PRODUCT: ModeStyle(dark="steel_blue3", light="slate_blue3"),
    ThemeTag.DOCSET: ModeStyle(dark="violet", light="dark_violet"),
}
"""Centralized mapping of semantic tags to their dark and light mode styles."""

DARK_THEME_STYLES: dict[ThemeTag, str] = {
    tag: mode.dark for tag, mode in THEME_STYLES.items()
}
"""Theme styles optimized for dark terminal backgrounds."""

LIGHT_THEME_STYLES: dict[ThemeTag, str] = {
    tag: mode.light for tag, mode in THEME_STYLES.items()
}
"""Theme styles optimized for light terminal backgrounds."""


DEFAULT_STYLES: dict[ThemeTag, str] = dict(DARK_THEME_STYLES)
"""Default semantic styles for docbuild CLI output (defaults to dark theme)."""


def get_theme(
    custom_styles: Mapping[str | ThemeTag, str] | None = None,
    preset: str = "dark",
) -> Theme:
    """Create a Rich Theme merging preset styles with any custom overrides.

    :param custom_styles: Optional dictionary or mapping of style names to Rich
        style specifications.
    :param preset: Base theme preset to start from ('dark' or 'light').
    :returns: A configured Rich Theme instance.
    :raises ValueError: If an unsupported preset name is provided.
    """
    preset_lower = preset.lower()
    if preset_lower == "dark":
        base = DARK_THEME_STYLES
    elif preset_lower == "light":
        base = LIGHT_THEME_STYLES
    else:
        raise ValueError(
            f"Invalid theme preset '{preset}'. "
            "Supported presets are 'dark' and 'light'."
        )

    merged: dict[str, str] = {str(k): v for k, v in base.items()}
    if custom_styles:
        merged.update(
            {
                str(k): v
                for k, v in custom_styles.items()
                if k not in ("preset", "mode")
            }
        )
    try:
        return Theme(merged)
    except StyleSyntaxError as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)


DOCBUILD_THEME: Theme = get_theme()
"""Pre-instantiated default Rich Theme for docbuild."""
