"""Defines the handling of metadata extraction from deliverables."""

import asyncio
import logging
from pathlib import Path
import shlex
import tempfile

from lxml import etree
from rich.console import Console

from ...config.xml.stitch import create_stitchfile
from ...constants import DEFAULT_DELIVERABLES
from ...models.deliverable import Deliverable
from ...models.doctype import Doctype
from ...utils.contextmgr import PersistentOnErrorTemporaryDirectory
from ..context import DocBuildContext

# Set up rich consoles for output
console_out = Console()
console_err = Console(stderr=True)

# Set up logging
log = logging.getLogger(__name__)


def get_deliverable_from_doctype(
    root: etree._ElementTree,
    context: DocBuildContext,
    doctype: Doctype,
) -> list[Deliverable]:
    """Get deliverable from doctype.

    :param root: The stitched XML node containing configuration.
    :param context: The DocBuildContext containing environment configuration.
    :param doctype: The Doctype object to process.
    :return: A list of deliverables for the given doctype.
    """
    console_out.print(f'Getting deliverable for doctype: {doctype}')
    console_out.print(f'XPath for {doctype}: {doctype.xpath()}')
    languages = root.getroot().xpath(f'./{doctype.xpath()}')

    return [
        Deliverable(node)
        for language in languages
        for node in language.findall('deliverable')
    ]


async def process_deliverable(
    deliverable: Deliverable,
    *,
    repo_dir: Path,
    temp_repo_dir: Path,
    base_cache_dir: Path,
    meta_cache_dir: Path,
    dapstmpl: str,
) -> bool:
    """Process a single deliverable.

    This function creates a temporary clone of the deliverable's repository,
    checks out the correct branch, and then executes the DAPS command to
    generate metadata.

    :param deliverable: The Deliverable object to process.
    :param repo_dir: The permanent repo path taken from the env
         config ``paths.repo_dir``
    :param temp_repo_dir: The temporary repo path taken from the env
         config ``paths.temp_repo_dir``
    :param base_cache_dir: The base path of the cache directory taken
         from the env config ``paths.base_cache_dir``
    :param meta_cache_dir: The ath of the metadata directory taken
         from the env config ``paths.meta_cache_dir``
    :param dapstmp: A template string with the daps command and potential
     placeholders
    :return: True if successful, False otherwise.
    :raises ValueError: If required configuration paths are missing.
    """
    console_out.print(f'> Processing deliverable: {deliverable.full_id}')

    meta_cache_dir = Path(meta_cache_dir)

    bare_repo_path = repo_dir / deliverable.git.slug
    if not bare_repo_path.is_dir():
        log.error(
            f'Bare repository not found for {deliverable.git.name} at {bare_repo_path}'
        )
        return False

    outputdir = meta_cache_dir / deliverable.relpath
    outputdir.mkdir(parents=True, exist_ok=True)

    prefix = (
        f'{deliverable.productid}-{deliverable.docsetid}-'
        f'{deliverable.lang}--{deliverable.dcfile}'
    )

    try:
        async with PersistentOnErrorTemporaryDirectory(
            dir=str(temp_repo_dir),
            prefix=f'clone-{prefix}_',
        ) as worktree_dir:
            # 1. Create a temporary clone from the bare repo and checkout a branch.
            clone_cmd = [
                'git',
                'clone',
                '--local',
                f'--branch={deliverable.branch}',
                str(bare_repo_path),
                str(worktree_dir),
            ]
            clone_process = await asyncio.create_subprocess_exec(
                *clone_cmd,
                stdin=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await clone_process.communicate()
            if clone_process.returncode != 0:
                # Raise an exception on failure to let the context manager know.
                raise RuntimeError(
                    f'Failed to clone {bare_repo_path}: {stderr.decode().strip()}'
                )

            # The source file for daps might be in a subdirectory
            dcfile_path = Path(deliverable.subdir) / deliverable.dcfile

            # 2. Run the daps command
            cmd = shlex.split(
                dapstmpl.format(
                    builddir=str(worktree_dir),
                    dcfile=str(worktree_dir / dcfile_path),
                    output=str(outputdir / deliverable.dcfile),
                )
            )
            console_out.print(f'  command: {cmd}')
            daps_process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await daps_process.communicate()
            if daps_process.returncode != 0:
                # Raise an exception on failure.
                raise RuntimeError(
                    f'DAPS command failed for {deliverable.full_id}: '
                    f'{stderr.decode().strip()}'
                )

        console_out.print(f'> Processed deliverable: {deliverable.pdlangdc}')
        return True

    except RuntimeError as e:
        # console_err.print(f'Error processing {deliverable.full_id}: {e}')
        log.error('Error processing %s: %s', deliverable.full_id, str(e) )
        return False


async def process_doctype(
    root: etree._ElementTree,
    context: DocBuildContext,
    doctype: Doctype,
) -> bool:
    """Process the doctypes and create metadata files.

    :param root: The stitched XML node containing configuration.
    :param context: The DocBuildContext containing environment configuration.
    :param doctypes: A tuple of Doctype objects to process.
    """
    # Here you would implement the logic to process the doctypes
    # and create metadata files based on the stitchnode and context.
    # This is a placeholder for the actual implementation.
    console_out.print(f'Processing doctypes: {doctype}')
    # xpath = doctype.xpath()
    # print("XPath: ", xpath)
    console_out.print(f'XPath: {doctype.xpath()}', markup=False)

    deliverables = await asyncio.to_thread(
        get_deliverable_from_doctype,
        root,
        context,
        doctype,
    )
    console_out.print(f'Found deliverables: {len(deliverables)}')
    dapsmetatmpl = context.envconfig.get('build', {}).get('daps', {}).get('meta', None)

    console_out.print(f'daps command: {dapsmetatmpl}', markup=False)

    repo_dir = context.envconfig.get('paths', {}).get('repo_dir', None)
    base_cache_dir = context.envconfig.get('paths', {}).get('base_cache_dir', None)
    # We retrieve the path.meta_cache_dir and fall back to path.base_cache_dir
    # if not available:
    meta_cache_dir = context.envconfig.get('paths', {}).get(
        'meta_cache_dir', base_cache_dir
    )
    # Cloned temporary repo:
    temp_repo_dir = context.envconfig.get('paths', {}).get('temp_repo_dir', None)

    # Check all paths:
    if not all((repo_dir, base_cache_dir, temp_repo_dir, meta_cache_dir)):
        raise ValueError(
            'Missing required paths in configuration: '
            f'{repo_dir=}, {base_cache_dir=}, {temp_repo_dir=}, {meta_cache_dir=}'
        )

    # Ensure base directories exist
    temp_repo_dir = Path(temp_repo_dir)
    meta_cache_dir = Path(meta_cache_dir)
    base_cache_dir = Path(base_cache_dir)
    repo_dir = Path(repo_dir)
    temp_repo_dir.mkdir(parents=True, exist_ok=True)
    meta_cache_dir.mkdir(parents=True, exist_ok=True)
    base_cache_dir.mkdir(parents=True, exist_ok=True)
    repo_dir.mkdir(parents=True, exist_ok=True)

    tasks = [
        process_deliverable(
            deliverable,
            repo_dir=repo_dir,
            temp_repo_dir=temp_repo_dir,
            base_cache_dir=base_cache_dir,
            meta_cache_dir=meta_cache_dir,
            dapstmpl=dapsmetatmpl,
        )
        for deliverable in deliverables
    ]
    results = await asyncio.gather(*tasks)

    return all(results)


async def process(
    context: DocBuildContext,
    doctypes: tuple[Doctype],
) -> int:
    """Asynchronous function to process metadata retrieval.

    :param context: The DocBuildContext containing environment configuration.
    :param xmlfiles: A tuple or iterator of XML file paths to validate.
    :raises ValueError: If no envconfig is found or if paths are not
        configured correctly.
    :return: 0 if all files passed validation, 1 if any failures occurred.
    """
    if context.envconfig is None:
        raise ValueError('No envconfig found in context.')

    configdir = context.envconfig.get('paths', {}).get('config_dir', None)
    if configdir is None:
        raise ValueError('Could not get a value from envconfig.paths.config_dir')
    configdir = Path(configdir).expanduser()
    console_out.print(f'Config path: {configdir}')
    xmlconfigs = tuple(configdir.rglob('[a-z]*.xml'))
    stitchnode = await create_stitchfile(xmlconfigs)
    console_out.print(f'Stitch node: {stitchnode.getroot().tag}')
    console_out.print(f'Deliverables: {len(stitchnode.xpath(".//deliverable"))}')

    if not doctypes:
        doctypes = [Doctype.from_str(DEFAULT_DELIVERABLES)]

    tasks = [process_doctype(stitchnode, context, dt) for dt in doctypes]
    results = await asyncio.gather(*tasks)
    console_out.print(f'Results: {results}')
    return 0
