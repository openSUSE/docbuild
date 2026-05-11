"""Validate Portal XML configuration."""

import asyncio
import logging
from pathlib import Path

import click
from rich.console import Console

from ...cli.context import DocBuildContext
from ...constants import PORTALLOGGER_NAME
from . import process as process_mod

# ---- Logger setup
log = logging.getLogger(__name__)
portal_log = logging.getLogger(PORTALLOGGER_NAME)

# ---- Console setup
console_out = Console()
console_err = Console(stderr=True)


@click.command(help=__doc__)
@click.option(
    "-M", "--main-portal-config",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to the main Portal XML configuration file. Overrides env config.",
)
@click.option(
    "-S", "--portal-schema",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to the Portal RELAX NG schema file. Overrides env config.",
)
@click.pass_context
def validate(
    ctx: click.Context,
    main_portal_config: Path,
    portal_schema: Path,
) -> None:
    """Subcommand to validate XML configuration files.

    :param ctx: The Click context object.
    :param main_portal_config: main Portal XML config file to validate.
    :param portal_schema: Portal schema file to use for validation.
    """
    context: DocBuildContext = ctx.obj
    env = context.envconfig

    configdir = env.paths.config_dir
    configdir_path = Path(configdir).expanduser()
    if not main_portal_config:
        main_portal_config = env.paths.main_portal_config.expanduser()
    else:
        main_portal_config = Path(main_portal_config).expanduser()

    if not portal_schema:
        portal_schema = env.paths.portal_rncschema.expanduser()
    else:
        portal_schema = Path(portal_schema).expanduser()

    log.debug("Config directory: %s", configdir_path)
    log.debug("Main Portal XML config file: %s", main_portal_config)
    log.debug("Portal schema file: %s", portal_schema)

    result = asyncio.run(
        process_mod.process(context, main_portal_config, portal_schema)
    )

    ctx.exit(result)  # Use the result as the exit code for the CLI
