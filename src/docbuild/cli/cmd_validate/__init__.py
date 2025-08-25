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
@click.option(
    '--validation-method',
    type=click.Choice(['jing', 'lxml'], case_sensitive=False),
    default='jing',
    help="Choose validation method: 'jing' or 'lxml'",
)
@click.pass_context
def validate(ctx: click.Context, xmlfiles: tuple | Iterator[Path], validation_method: str) -> None:
    """Subcommand to validate XML configuration files.

    :param ctx: The Click context object.
    :param xmlfiles: XML files to validate, if empty all XMLs in config dir are used.
    :param validation_method: Validation method to use, 'jing' or 'lxml'.
    """
    context: DocBuildContext = ctx.obj

    # Set the chosen validation method in the context for downstream use
    context.validation_method = validation_method.lower()

    if context.envconfig is None:
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

    log.info(f'Validating XML configuration files using {validation_method} method')

    result = asyncio.run(process_mod.process(context, xmlfiles=xml_files_to_process))

    ctx.exit(result)  # Use the result as the exit code for the CLI
