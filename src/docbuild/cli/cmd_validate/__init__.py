"""CLI interface to validate XML configuration files."""

import asyncio
from collections.abc import Iterator
import logging
from pathlib import Path

import click

from ..context import DocBuildContext
from . import process as process_mod

log = logging.getLogger(__name__)


@click.command(help=__doc__)
@click.argument(
    'xmlfiles',
    nargs=-1,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.pass_context
def validate(ctx: click.Context, xmlfiles: tuple | Iterator[Path]) -> None:
    """Subcommand to validate XML configuration files.

    :param ctx: The Click context object.
    """
    context: DocBuildContext = ctx.obj
    if context.envconfig is None:
        # log.critical('No envconfig found in context.')
        raise ValueError('No envconfig found in context.')

    if (paths := ctx.obj.envconfig.get('paths')) is None:
        raise ValueError('No paths found in envconfig.')

    configdir = paths.get('config_dir', None)
    if configdir is None:
        raise ValueError('Could not get a value from envconfig.paths.config_dir')

    configdir_path = Path(configdir).expanduser()

    if not xmlfiles:
        xml_files_to_process = tuple(configdir_path.rglob('[a-z]*.xml'))
    else:
        xml_files_to_process = xmlfiles

    log.info('Validating XML configuration files')

    result = asyncio.run(process_mod.process(context, xmlfiles=xml_files_to_process))

    ctx.exit(result)  # Use the result as the exit code for the CLI
