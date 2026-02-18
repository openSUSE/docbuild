"""Main CLI tool for document operations."""

from collections.abc import Sequence
import logging
from pathlib import Path
import sys
from typing import Any, cast

import click
from pydantic import BaseModel, ValidationError
import rich.console
from rich.traceback import install as install_traceback

from ..__about__ import __version__
from ..config.load import handle_config
from ..constants import (
    APP_CONFIG_BASENAMES,
    APP_NAME,
    CONFIG_PATHS,
    DEFAULT_ENV_CONFIG_FILENAME,
    PROJECT_DIR,
    PROJECT_LEVEL_APP_CONFIG_FILENAMES,
)
from ..logging import setup_logging
from ..models.config.app import AppConfig
from ..models.config.env import EnvConfig
from ..utils.errors import format_pydantic_error
from ..utils.pidlock import LockAcquisitionError, PidFileLock
from .cmd_build import build
from .cmd_c14n import c14n
from .cmd_check import cmd_check
from .cmd_config import config
from .cmd_metadata import metadata
from .cmd_repo import repo
from .cmd_validate import validate
from .context import DocBuildContext
from .defaults import DEFAULT_APP_CONFIG, DEFAULT_ENV_CONFIG

PYTHON_VERSION = (
    f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
)
log = logging.getLogger(__name__)
CONSOLE = rich.console.Console(stderr=True, highlight=False)


def _setup_console() -> None:
    """Configure the rich console."""
    install_traceback(console=CONSOLE, show_locals=True)


def handle_validation_error(
    e: Exception,
    model_class: type[BaseModel],
    config_files: Sequence[Path] | None,
    verbose: int,
    ctx: click.Context,
) -> None:
    """Format validation errors and exit the CLI.

    Outsourced logic to avoid code duplication between App and Env config phases.
    Using Sequence[Path] ensures compatibility with both lists and tuples.
    :param e: The exception that was raised during validation.
    :param model_class: The Pydantic model class that was being validated
      (AppConfig or EnvConfig).
    :param config_files: The list of config files that were attempted to be loaded, used for error context.
    :param verbose: The verbosity level from the CLI options, which can be
      used to control the level of detail in the error output.
    :param ctx: The Click context, used to exit the CLI with an appropriate
      status code after handling the error.
    """
    config_label = "Application" if model_class == AppConfig else "Environment"

    if isinstance(e, ValidationError):
        # Safely extract the first config file name for the error header
        config_file = str((config_files or ["unknown"])[0])
        format_pydantic_error(
            e, model_class, config_file, verbose, console=CONSOLE
        )
    else:
        log.error("%s configuration failed validation:", config_label)
        log.error("Error in config file(s): %s", config_files)
        log.error(e)
    ctx.exit(1)


@click.group(
    name=APP_NAME,
    context_settings={"show_default": True, "help_option_names": ["-h", "--help"]},
    help="Main CLI tool for document operations.",
    invoke_without_command=True,
)
@click.version_option(
    __version__,
    prog_name=APP_NAME,
    message=f"%(prog)s, version %(version)s running Python {PYTHON_VERSION}",
)
@click.option("-v", "--verbose", count=True, help="Increase verbosity")
@click.option("--dry-run", is_flag=True, help="Run without making changes")
@click.option(
    "--debug/--no-debug",
    default=False,
    envvar="DOCBUILD_DEBUG",
    help=(
        "Enable debug mode. "
        "This will show more information about the process and the config files. "
        "If available, read the environment variable ``DOCBUILD_DEBUG``."
    ),
)
@click.option(
    "--app-config",
    metavar="APP_CONFIG_FILE",
    type=click.Path(
        exists=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        path_type=Path,
    ),
    help="Filename to the application TOML config file. Overrides auto-search.",
)
@click.option(
    "--env-config",
    metavar="ENV_CONFIG_FILE",
    type=click.Path(exists=True, dir_okay=False),
    help=(
        "Filename to a environment's TOML config file. "
        f"If not set, {APP_NAME} uses the default filename "
        f"{DEFAULT_ENV_CONFIG_FILENAME!r} "
        "in the current working directory."
    ),
)
@click.pass_context
def cli(
    ctx: click.Context,
    verbose: int,
    dry_run: bool,
    debug: bool,
    app_config: Path,
    env_config: Path,
    **kwargs: dict,
) -> None:
    """Acts as a main entry point for CLI tool.

    :param ctx: The Click context object.
    :param verbose: The verbosity level.
    :param dry_run: If set, just pretend to run the command without making any changes.
    :param debug: If set, enable debug mode.
    :param app_config: Filename to the application TOML config file.
    :param env_config: Filename to a environment's TOML config file.
    :param kwargs: Additional keyword arguments.
    """
    if ctx.invoked_subcommand is None:
        click.echo(10 * "-")
        click.echo(ctx.get_help())
        ctx.exit(0)

    if ctx.obj is None:
        ctx.ensure_object(DocBuildContext)

    context = ctx.obj
    context.verbose = verbose
    context.dry_run = dry_run
    context.debug = debug

    # --- PHASE 1: Load and Validate Application Config ---
    (
        context.appconfigfiles,
        raw_appconfig,
        context.appconfig_from_defaults,
    ) = handle_config(
        app_config,
        CONFIG_PATHS,
        APP_CONFIG_BASENAMES + PROJECT_LEVEL_APP_CONFIG_FILENAMES,
        None,
        DEFAULT_APP_CONFIG,
    )

    raw_appconfig = cast(dict[str, Any], raw_appconfig)

    try:
        context.appconfig = AppConfig.from_dict(raw_appconfig)
    except (ValueError, ValidationError) as e:
        handle_validation_error(e, AppConfig, context.appconfigfiles, verbose, ctx)

    # 3. Setup logging using the validated config object
    logging_config = context.appconfig.logging.model_dump(
        by_alias=True, exclude_none=True
    )
    setup_logging(cliverbosity=verbose, user_config={"logging": logging_config})

    # --- PHASE 2: Load Environment Config, Validate, and Acquire Lock ---
    (
        context.envconfigfiles,
        raw_envconfig,
        context.envconfig_from_defaults,
    ) = handle_config(
        env_config,
        (PROJECT_DIR,),
        None,
        DEFAULT_ENV_CONFIG_FILENAME,
        DEFAULT_ENV_CONFIG,
    )

    raw_envconfig = cast(dict[str, Any], raw_envconfig)

    try:
        context.envconfig = EnvConfig.from_dict(raw_envconfig)
    except (ValueError, ValidationError) as e:
        handle_validation_error(e, EnvConfig, context.envconfigfiles, verbose, ctx)

    env_config_path = (context.envconfigfiles or [None])[0]

    # --- CONCURRENCY CONTROL ---
    if env_config_path:
        ctx.obj.env_lock = PidFileLock(resource_path=cast(Path, env_config_path))
        try:
            ctx.obj.env_lock.__enter__()
            log.info("Acquired lock for environment config: %r", env_config_path.name)
        except LockAcquisitionError as e:
            log.error(str(e))
            ctx.exit(1)
        except Exception as e:
            log.error("Failed to set up environment lock: %s", e)
            ctx.exit(1)

        ctx.call_on_close(lambda: ctx.obj.env_lock.__exit__(None, None, None))


# Add subcommands
cli.add_command(build)
cli.add_command(c14n)
cli.add_command(config)
cli.add_command(repo)
cli.add_command(metadata)
cli.add_command(validate)
cli.add_command(cmd_check)
