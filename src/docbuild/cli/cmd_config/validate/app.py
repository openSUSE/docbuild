"""Validation functions for application configuration settings."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich.console import Console

    from docbuild.cli.context import DocBuildContext

def validate_app_settings(ctx_obj: DocBuildContext, console: Console) -> bool:
    """Validate application-specific TOML settings.

    :param ctx_obj: The context object containing the loaded configuration.
    :param console: The Rich console object for printing messages.
    :return: True if the application configuration is valid, False otherwise.
    """
    if ctx_obj.appconfig:
        console.print("✅ [bold]Application Configuration:[/bold] Valid")

        # FIX: Provide an empty tuple as fallback to prevent 'None' iteration error
        config_files = ctx_obj.appconfigfiles or ()

        for f in config_files:
            console.print(f"   [dim]- {f}[/dim]")
        return True
    return False
