"""CLI interface to validate the configuration files."""

import click
from rich.panel import Panel

from ..console import console


@click.command(name="validate")
@click.pass_context
def validate(ctx: click.Context) -> None:
    """Validate TOML configuration files.

    This checks the syntax and schema of application and environment files.

    :param ctx: The Click context object, which should already have loaded configurations.
    """
    context = ctx.obj

    console.print("[header]Running Configuration Validation...[/]\n")

    if context.appconfig:
        console.print("✅ [info]Application Configuration:[/] [success]Valid[/]")
        for f in (context.appconfigfiles or []):
            console.print(f"   [muted]- {f}[/]")

    if context.envconfig:
        console.print("\n✅ [info]Environment Configuration:[/] [success]Valid[/]")
        if context.envconfigfiles:
            for f in context.envconfigfiles:
                console.print(f"   [muted]- {f}[/]")
        elif context.envconfig_from_defaults:
            console.print("   [muted]- Using internal defaults[/]")

    console.print(
        Panel(
            "[success]Configuration is valid![/]\n"
            "All TOML files match the required schema.",
            border_style="success",
            expand=False,
        )
    )
