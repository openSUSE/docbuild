"""CLI interface to preview theme presets and active styling."""

import click
from rich.console import Console
from rich.table import Table
from rich.theme import Theme

from ..console import console
from ..theme import DARK_THEME_STYLES, LIGHT_THEME_STYLES, ThemeTag, get_theme


@click.command(name="theme")
@click.option(
    "--preset",
    type=click.Choice(["dark", "light", "all"], case_sensitive=False),
    default="all",
    show_default=True,
    help="Theme preset to display ('dark', 'light', or 'all').",
)
@click.pass_context
def theme_cmd(ctx: click.Context, preset: str) -> None:
    """Preview built-in theme presets and the active theme configuration.

    Displays visual showcase tables with live rendering of each semantic token.
    """
    context = ctx.obj
    presets_to_show = ("dark", "light") if preset == "all" else (preset.lower(),)

    # 1. Display requested built-in presets
    for preset_name in presets_to_show:
        preset_theme = get_theme(preset=preset_name)
        con = Console(theme=preset_theme)
        table = Table(
            title=f"Built-in Theme Preset: {preset_name.capitalize()}",
            header_style="header",
        )
        table.add_column("Semantic Token", style="bold")
        table.add_column("Style Definition", style="muted")
        table.add_column("Sample Output")

        for tag in ThemeTag:
            style_def = (
                DARK_THEME_STYLES[tag]
                if preset_name == "dark"
                else LIGHT_THEME_STYLES[tag]
            )
            sample = f"[{tag.value}]Sample {tag.value} text[/]"
            table.add_row(tag.value, style_def, sample)

        console.print()
        con.print(table)

    # 2. Display active configuration theme if custom app configuration is loaded
    if (
        context
        and context.appconfig
        and hasattr(context.appconfig, "theme")
        and context.appconfigfiles
        and not context.appconfig_from_defaults
    ):
        active_theme = Theme(
            {str(k): v for k, v in context.appconfig.theme.items()}
        )
        con = Console(theme=active_theme)
        source_label = context.appconfigfiles[0]
        table = Table(
            title=f"Active Configuration Theme ({source_label})",
            header_style="header",
        )
        table.add_column("Semantic Token", style="bold")
        table.add_column("Active Style", style="muted")
        table.add_column("Sample Output")

        for tag in ThemeTag:
            active_style = context.appconfig.theme[tag]
            sample = f"[{tag.value}]Sample {tag.value} text[/]"
            table.add_row(tag.value, active_style, sample)

        console.print()
        con.print(table)
