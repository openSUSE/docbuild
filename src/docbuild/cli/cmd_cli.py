"""Main CLI tool for document operations."""

from pathlib import Path
import sys
import logging
import click
import rich.console
import rich.logging
from rich.pretty import install
from rich.traceback import install as install_traceback
from pydantic import ValidationError
from typing import Any, cast 

from ..__about__ import __version__
from ..config.app import replace_placeholders
from ..config.load import handle_config
from ..models.config.app import AppConfig
from ..models.config.env import EnvConfig

from ..constants import (
    APP_CONFIG_BASENAMES,
    APP_NAME,
    CONFIG_PATHS,
    DEFAULT_ENV_CONFIG_FILENAME,
    PROJECT_DIR,
    PROJECT_LEVEL_APP_CONFIG_FILENAMES,
)
from ..logging import setup_logging
from ..utils.pidlock import PidFileLock, LockAcquisitionError
from .cmd_build import build
from .cmd_c14n import c14n
from .cmd_config import config
from .cmd_metadata import metadata
from .cmd_repo import repo
from .cmd_validate import validate
from .context import DocBuildContext
from .defaults import DEFAULT_APP_CONFIG, DEFAULT_ENV_CONFIG

PYTHON_VERSION = (
    f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}'
)
log = logging.getLogger(__name__)
CONSOLE = rich.console.Console(stderr=True, highlight=False)

def _setup_console() -> None:
    """Configures the rich console."""
    install_traceback(console=CONSOLE, show_locals=True)

@click.group(
    name=APP_NAME,
    context_settings={'show_default': True, 'help_option_names': ['-h', '--help']},
    help='Main CLI tool for document operations.',
    invoke_without_command=True,
)
@click.version_option(
    __version__,
    prog_name=APP_NAME,
    message=f"%(prog)s, version %(version)s running Python {PYTHON_VERSION}",
)
@click.option('-v', '--verbose', count=True, help='Increase verbosity')
@click.option('--dry-run', is_flag=True, help='Run without making changes')
@click.option(
    '--debug/--no-debug',
    default=False,
    envvar='DOCBUILD_DEBUG',
    help=(
        'Enable debug mode. '
        'This will show more information about the process and the config files. '
        "If available, read the environment variable 'DOCBUILD_DEBUG'."
    ),
)
@click.option(
    '--app-config',
    metavar='APP_CONFIG_FILE',
    type=click.Path(
        exists=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        path_type=Path,
    ),
    help='Filename to the application TOML config file. Overrides auto-search.',
)
@click.option(
    '--env-config',
    metavar='ENV_CONFIG_FILE',
    type=click.Path(exists=True, dir_okay=False),
    help=(
        "Filename to a environment's TOML config file. "
        f'If not set, {APP_NAME} uses the default filename '
        f'{DEFAULT_ENV_CONFIG_FILENAME!r} '
        'in the current working directory.'
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
        # If no subcommand is invoked, show the help message
        click.echo(10 * '-')
        click.echo(ctx.get_help())
        ctx.exit(0)

    if ctx.obj is None:
        ctx.ensure_object(DocBuildContext)

    # Build the context object
    context = ctx.obj
    context.verbose = verbose
    context.dry_run = dry_run
    context.debug = debug
    
    # --- PHASE 1: Load and Validate Application Config (and setup logging) ---
    
    # 1. Load the raw application config dictionary
    (
        context.appconfigfiles,
        raw_appconfig, # Store config as raw dictionary
        context.appconfig_from_defaults,
    ) = handle_config(
        app_config,
        CONFIG_PATHS,
        APP_CONFIG_BASENAMES + PROJECT_LEVEL_APP_CONFIG_FILENAMES,
        None,
        DEFAULT_APP_CONFIG,
    )

    # Explicitly cast the raw_appconfig type to silence Pylance
    raw_appconfig = cast(dict[str, Any], raw_appconfig)

    # 2. Validate the raw config dictionary using Pydantic
    try:
        # Pydantic validation also handles placeholder replacement via @model_validator
        context.appconfig = AppConfig.from_dict(raw_appconfig)
    except (ValueError, ValidationError) as e:
        log.error("Application configuration failed validation:")
        log.error("Error in config file(s): %s", context.appconfigfiles)
        log.error(e)
        ctx.exit(1)

    # 3. Setup logging using the validated config object
    # Use model_dump(by_alias=True) to ensure the 'class' alias is used.
    logging_config = context.appconfig.logging.model_dump(by_alias=True, exclude_none=True)
    setup_logging(cliverbosity=verbose, user_config={'logging': logging_config})

    # --- PHASE 2: Load Environment Config, Validate, and Acquire Lock ---
    
    # 1. Load raw Environment Config
    (
        context.envconfigfiles,
        raw_envconfig, # Renaming context.envconfig to raw_envconfig locally
        context.envconfig_from_defaults,
    ) = handle_config(
        env_config,
        (PROJECT_DIR,),
        None,
        DEFAULT_ENV_CONFIG_FILENAME,
        DEFAULT_ENV_CONFIG,
    )
    
    # Explicitly cast the raw_envconfig type to silence Pylance
    raw_envconfig = cast(dict[str, Any], raw_envconfig)
    
    # 2. VALIDATE the raw environment config dictionary using Pydantic
    try:
        # Pydantic validation handles placeholder replacement via @model_validator
        # The result is the validated Pydantic object, stored in context.envconfig
        context.envconfig = EnvConfig.from_dict(raw_envconfig)
    except (ValueError, ValidationError) as e:
        log.error(
             "Environment configuration failed validation: "
             "Error in config file(s): %s %s",
             context.envconfigfiles, e
        )
        ctx.exit(1)
    
    env_config_path = context.envconfigfiles[0] if context.envconfigfiles else None
    
    # --- CONCURRENCY CONTROL: Use explicit __enter__ and cleanup registration ---
    if env_config_path:
        # 1. Instantiate the lock object
        ctx.obj.env_lock = PidFileLock(resource_path=env_config_path)
        
        try:
            # 2. Acquire the lock by explicitly calling the __enter__ method.
            ctx.obj.env_lock.__enter__()
            log.info("Acquired lock for environment config: %r", env_config_path.name)

        except LockAcquisitionError as e:
            # Handles lock contention
            log.error(str(e))
            ctx.exit(1)
        except Exception as e:
            # Handles critical errors
            log.error("Failed to set up environment lock: %s", e)
            ctx.exit(1)
        
        # 3. Register the lock's __exit__ method to be called when the context terminates.
        # We use a lambda to supply the three mandatory positional arguments (None)
        # expected by __exit__, satisfying the click.call_on_close requirement.
        ctx.call_on_close(lambda: ctx.obj.env_lock.__exit__(None, None, None))
    
# Add subcommand
cli.add_command(build)
cli.add_command(c14n)
cli.add_command(config)
cli.add_command(repo)
cli.add_command(metadata)
cli.add_command(validate)