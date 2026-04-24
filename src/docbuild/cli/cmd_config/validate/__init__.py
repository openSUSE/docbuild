"""Module for the 'validate' command orchestrating config and portal validation."""

import asyncio

import click
from rich.console import Console
from rich.panel import Panel

from .app import validate_app_settings
from .env import validate_env_settings
from .portal import validate_portal_content


@click.command(name="validate")
@click.option(
    "--portal",
    "portal_flag",
    is_flag=True,
    help="Validate only the portal settings (RNG/Stitch)",
)
@click.option(
    "--env", "env_flag", is_flag=True, help="Validate only the environment settings"
)
@click.option("--app", "app_flag", is_flag=True, help="Validate only the app settings")
@click.option(
    "--all", "all_flag", is_flag=True, help="Validate everything (default behavior)"
)
@click.pass_context
def validate_config(
    ctx: click.Context, portal_flag: bool, env_flag: bool, app_flag: bool, all_flag: bool
) -> None:
    """Validate configuration files and portal content.

    :param ctx: The Click context object containing the loaded configuration.
    :param portal_flag: Whether to validate only the portal settings.
    :param env_flag: Whether to validate only the environment settings.
    :param app_flag: Whether to validate only the application settings.
    :param all_flag: Whether to validate all settings (overrides other flags).
    """
    # Determine which tasks to run.
    # If --all is set, or NO specific flags are set, we run everything.
    run_all = all_flag or not (portal_flag or env_flag or app_flag)

    tasks = {
        "app": run_all or app_flag,
        "env": run_all or env_flag,
        "portal": run_all or portal_flag,
    }

    # Run the async helper and capture the success boolean
    success = asyncio.run(_async_validate_config(ctx, tasks))

    if not success:
        ctx.exit(1)


async def _async_validate_config(ctx: click.Context, tasks: dict[str, bool]) -> bool:
    """Asynchronous helper function to perform selected validations.

    :param ctx: The Click context object.
    :param tasks: Dictionary mapping validation components to their run status.
    :return: True if all attempted validations passed, False otherwise.
    """
    context = ctx.obj
    console = Console()

    # Ensure context exists (important for tests)
    if context is None:
        return False

    mode_label = "Full" if all(tasks.values()) else "Partial"
    console.print(f"[bold blue]Running {mode_label} Configuration Validation...[/bold blue]\n")

    results = []

    # 1. Validate App Settings (Sync)
    if tasks["app"]:
        results.append(validate_app_settings(context, console))

    # 2. Validate Env Settings (Sync)
    if tasks["env"]:
        results.append(validate_env_settings(context, console))

    # 3. Validate Portal Content (Async)
    if tasks["portal"]:
        results.append(await validate_portal_content(context, console))

    # Calculate overall success. Note: if no tasks were run (impossible via CLI),
    # all([]) is True, which is safe.
    success = all(results)

    if success:
        summary_msg = (
            "Configuration is fully valid!" if all(tasks.values())
            else "Requested validation checks passed!"
        )
        console.print(
            Panel(
                f"[bold green]{summary_msg}[/bold green]",
                border_style="green",
                expand=False,
            )
        )
        return True

    return False
