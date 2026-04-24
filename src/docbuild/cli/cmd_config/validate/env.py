"""Validation functions for environment configuration settings."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich.console import Console

    from docbuild.cli.context import DocBuildContext

def validate_env_settings(ctx_obj: DocBuildContext, console: Console) -> bool:
    """Validate environment-specific TOML settings.

    :param ctx_obj: The context object containing the loaded configuration.
    :param console: The Rich console object for printing messages.
    :return: True if the environment configuration is valid, False otherwise.
    """
    if ctx_obj.envconfig:
        console.print("\n✅ [bold]Environment Configuration:[/bold] Valid")

        env_files = ctx_obj.envconfigfiles or ()

        for f in env_files:
            console.print(f"   [dim]- {f}[/dim]")
        return True
    return False
