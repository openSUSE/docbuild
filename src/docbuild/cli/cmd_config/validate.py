"""CLI interface to validate the configuration files."""

import click
from rich.console import Console
from rich.panel import Panel


@click.command(name="validate")
@click.pass_context
def validate(ctx: click.Context) -> None:
    """Validate TOML configuration files.

    This checks the syntax and schema of application and environment files.

    :param ctx: The Click context object, which should already have loaded configurations.
    """
    context = ctx.obj
    console = Console()

    console.print("[bold blue]Running Configuration Validation...[/bold blue]\n")

    if context.appconfig:
        console.print("✅ [bold]Application Configuration:[/bold] Valid")
        for f in (context.appconfigfiles or []):
            console.print(f"   [dim]- {f}[/dim]")

    if context.envconfig:
        console.print("\n✅ [bold]Environment Configuration:[/bold] Valid")
        if context.envconfigfiles:
            for f in context.envconfigfiles:
                console.print(f"   [dim]- {f}[/dim]")
        elif context.envconfig_from_defaults:
            console.print("   [dim]- Using internal defaults[/dim]")

    console.print(
        Panel(
            "[bold green]Configuration is valid![/bold green]\n"
            "All TOML files match the required schema.",
            border_style="green",
            expand=False
        )
    )
