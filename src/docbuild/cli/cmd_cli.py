"""Main CLI tool for document operations."""

from pathlib import Path

import click

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
from .cmd_build import build
from .cmd_c14n import c14n
from .cmd_validate import validate
from .config import config
from .context import DocBuildContext
from .defaults import DEFAULT_APP_CONFIG, DEFAULT_ENV_CONFIG


@click.group(
    name=APP_NAME,
    context_settings={'show_default': True, 'help_option_names': ['-h', '--help']},
    help='Main CLI tool for document operations.',
    invoke_without_command=True,
)
@click.version_option(
    __version__,
    # package_name=,
    prog_name=__package__,
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
    setup_logging(cliverbosity=verbose)

    if ctx.invoked_subcommand is None:
        # If no subcommand is invoked, show the help message
        click.echo(10* '-')
        click.echo(ctx.get_help())
        ctx.exit(0)

    if ctx.obj is None:
        ctx.ensure_object(DocBuildContext)

    # Build the context object
    context = ctx.obj
    context.verbose = verbose
    context.dry_run = dry_run
    context.debug = debug
    # Set the defaults. Will be overridden if config files are provided.
    (
        context.appconfigfiles,
        context.appconfig,
        context.appconfig_from_defaults,
    ) = handle_config(
        app_config,
        CONFIG_PATHS,
        APP_CONFIG_BASENAMES + PROJECT_LEVEL_APP_CONFIG_FILENAMES,
        None,
        DEFAULT_APP_CONFIG,
    )
    (
        context.envconfigfiles,
        context.envconfig,
        context.envconfig_from_defaults,
    ) = handle_config(
        env_config,
        (PROJECT_DIR,),
        None,
        DEFAULT_ENV_CONFIG_FILENAME,
        DEFAULT_ENV_CONFIG,
    )


# Add subcommand
cli.add_command(build)
cli.add_command(c14n)
cli.add_command(config)
cli.add_command(validate)
