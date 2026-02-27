"""Defines the handling of metadata extraction from deliverables."""

import asyncio
from collections.abc import Generator, Sequence
import json
import logging
from pathlib import Path
import shlex
from typing import Any

from lxml import etree
from pydantic import ValidationError
from rich.console import Console

from ...config.xml.stitch import create_stitchfile
from ...constants import DEFAULT_DELIVERABLES
from ...models.deliverable import Deliverable
from ...models.doctype import Doctype
from ...models.manifest import Category, Description, Document, Manifest
from ...utils.contextmgr import PersistentOnErrorTemporaryDirectory, edit_json
from ...utils.git import ManagedGitRepo
from ..context import DocBuildContext

# Set up rich consoles for output
stdout = Console()
console_err = Console(stderr=True, style="red")

# Set up logging
log = logging.getLogger(__name__)


def get_deliverable_from_doctype(
    root: etree._ElementTree,
    doctype: Doctype,
) -> list[Deliverable]:
    """Get deliverable from doctype.

    :param root: The stitched XML node containing configuration.
    :param doctype: The Doctype object to process.
    :return: A list of deliverables for the given doctype.
    """
    # stdout.print(f'Getting deliverable for doctype: {doctype}')
    # stdout.print(f'XPath for {doctype}: {doctype.xpath()}')
    languages = root.getroot().xpath(f"./{doctype.xpath()}")

    return [
        Deliverable(node)
        for language in languages
        for node in language.findall("deliverable")
    ]


def collect_files_flat(
    doctypes: Sequence[Doctype],
    basedir: Path | str,
) -> Generator[tuple[Doctype, str, list[Path]], Any, None]:
    """Recursively collect all DC-metadata files from the cache directory.

    :param doctypes: Sequence of Doctype objects to filter by.
    :param basedir: The base directory to start the recursive search.
    :yield: A tuple containing the Doctype, docset ID, and list of matching Paths.
    """
    basedir = Path(basedir)
    task_stream = ((dt, ds) for dt in doctypes for ds in dt.docset)

    for dt, docset in task_stream:
        all_files = list(basedir.rglob("DC-*"))

        # Case-insensitive filtering
        files = [
            f for f in all_files
            if dt.product.value.lower() in [p.lower() for p in f.parts]
            and docset.lower() in [p.lower() for p in f.parts]
        ]

        if files:
            yield dt, docset, files

def get_daps_command(
    worktree_dir: Path,
    dcfile_path: Path,
    outputjson: Path,
    dapstmpl: str,
) -> list[str]:
    """Construct the DAPS command for native execution."""
    raw_daps_cmd = dapstmpl.format(
        builddir=str(worktree_dir),
        dcfile=str(dcfile_path),
        output=str(outputjson),
    )
    return shlex.split(raw_daps_cmd)


def update_metadata_json(outputjson: Path, deliverable: Deliverable) -> None:
    """Update the generated metadata JSON with deliverable-specific details."""
    fmt = deliverable.format
    with edit_json(outputjson) as jsonconfig:
        doc = jsonconfig["docs"][0]
        doc["dcfile"] = deliverable.dcfile
        doc["format"]["html"] = deliverable.html_path
        if fmt.get("pdf"):
            doc["format"]["pdf"] = deliverable.pdf_path
        if fmt.get("single-html"):
            doc["format"]["single-html"] = deliverable.singlehtml_path
        if not doc.get("lang"):
            doc["lang"] = deliverable.lang

async def process_deliverable(
    context: DocBuildContext,
    deliverable: Deliverable,
    *,
    dapstmpl: str,
) -> tuple[bool, Deliverable]:
    """Process a single deliverable asynchronously.

    This function creates a temporary clone of the deliverable's repository,
    checks out the correct branch, and then executes the DAPS command to
    generate metadata.

    :param context: The DocBuildContext containing environment configuration.
    :param deliverable: The Deliverable object to process.
    :param dapstmpl: A template string with the daps command and potential
     placeholders.
    :return: True if successful, False otherwise.
    """
    log.info("> Processing deliverable: %s", deliverable.full_id)

    # Simplified initialization
    env = context.envconfig
    repo_dir = env.paths.repo_dir
    tmp_repo_dir = env.paths.tmp_repo_dir
    meta_cache_dir = env.paths.meta_cache_dir

    bare_repo_path = repo_dir / deliverable.git.slug
    if not bare_repo_path.is_dir():
        log.error("Bare repository not found for %s at %s", deliverable.git.name, bare_repo_path)
        return False, deliverable

    outputdir = meta_cache_dir / deliverable.relpath
    outputdir.mkdir(parents=True, exist_ok=True)
    outputjson = outputdir / deliverable.dcfile

    try:
        async with PersistentOnErrorTemporaryDirectory(
            dir=str(tmp_repo_dir),
            prefix=f"clone-{deliverable.productid}-{deliverable.docsetid}-{deliverable.lang}-{deliverable.dcfile}_",
        ) as worktree_dir:
            mg = ManagedGitRepo(deliverable.git.url, repo_dir)
            if not await mg.clone_bare():
                raise RuntimeError(f"Failed to ensure bare repository for {deliverable.full_id}")

            try:
                await mg.create_worktree(worktree_dir, deliverable.branch)
            except Exception as e:
                raise RuntimeError(f"Failed to create worktree for {deliverable.full_id}: {e}") from e

            # Use absolute path within worktree to avoid DAPS "Missing DC-file" error
            full_dcfile_path = Path(worktree_dir) / deliverable.subdir / deliverable.dcfile

            cmd = get_daps_command(
                Path(worktree_dir),
                full_dcfile_path,
                outputjson,
                dapstmpl
            )

            daps_proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr_data = await daps_proc.communicate()

            if daps_proc.returncode != 0:
                log.error("DAPS Error: %s", stderr_data.decode())
                raise RuntimeError(f"DAPS failed for {deliverable.full_id}")

        update_metadata_json(outputjson, deliverable)
        log.debug("Updated metadata JSON for %s", deliverable.full_id)
        return True, deliverable

    except Exception as e:
        log.error("Error processing %s: %s", deliverable.full_id, str(e))
        return False, deliverable

async def update_repositories(
    deliverables: list[Deliverable], bare_repo_dir: Path
) -> bool:
    """Update all Git repositories associated with the deliverables.

    :param deliverables: A list of Deliverable objects.
    :param bare_repo_dir: The root directory for storing permanent bare clones.
    """
    log.info("Updating Git repositories...")
    unique_urls = {d.git.url for d in deliverables}
    repos = [ManagedGitRepo(url, bare_repo_dir) for url in unique_urls]

    tasks = [repo.clone_bare() for repo in repos]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    res = True
    for repo, result in zip(repos, results, strict=False):
        if isinstance(result, Exception) or not result:
            log.error("Failed to update repository %s", repo.slug)
            res = False

    return res


async def run_tasks_fail_fast(tasks: list[asyncio.Task]) -> list[Deliverable]:
    """Execute tasks and stop immediately on the first failure."""
    failed: list[Deliverable] = []
    for task in asyncio.as_completed(tasks):
        try:
            success, deliverable = await task
            if not success:
                failed.append(deliverable)
                for t in tasks:
                    if not t.done():
                        t.cancel()
                break
        except Exception as e:
            log.error("Task failed unexpectedly: %s", e)
            for t in tasks:
                if not t.done():
                    t.cancel()
            break
    return failed


async def run_tasks_collect_all(
    tasks: list[asyncio.Task], deliverables: list[Deliverable]
) -> list[Deliverable]:
    """Execute all tasks and collect every failure encountered."""
    failed: list[Deliverable] = []
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for deliverable, result in zip(deliverables, results, strict=False):
        if isinstance(result, tuple):
            success, res_deliverable = result
            if not success:
                failed.append(res_deliverable)
        elif isinstance(result, Exception):
            log.error("Error in task for %s: %s", deliverable.full_id, result)
            failed.append(deliverable)
    return failed


async def _run_metadata_tasks(
    tasks: list[asyncio.Task], deliverables: list[Deliverable], exitfirst: bool
) -> list[Deliverable]:
    """Execute metadata tasks using either fail-fast or collect-all strategy."""
    if exitfirst:
        return await run_tasks_fail_fast(tasks)
    return await run_tasks_collect_all(tasks, deliverables)

async def process_doctype(
    root: etree._ElementTree,
    context: DocBuildContext,
    doctype: Doctype,
    *,
    exitfirst: bool = False,
    skip_repo_update: bool = False,
) -> list[Deliverable]:
    """Process the doctypes and create metadata files.

    :param root: The stitched XML node containing configuration.
    :param context: The DocBuildContext containing environment configuration.
    :param doctype: The Doctype object to process.
    :param exitfirst: If True, stop processing on the first failure.
    :param skip_repo_update: If True, do not fetch updates for the git repositories.
    :return: A list of failed Deliverables.
    """
    env = context.envconfig
    repo_dir: Path = env.paths.repo_dir

    deliverables: list[Deliverable] = await asyncio.to_thread(
        get_deliverable_from_doctype, root, doctype
    )

    if skip_repo_update:
        log.info("Skipping repository %s updates as requested.", repo_dir)
    else:
        await update_repositories(deliverables, repo_dir)

    dapsmetatmpl = env.build.daps.meta
    tasks = [
        asyncio.create_task(process_deliverable(context, d, dapstmpl=dapsmetatmpl))
        for d in deliverables
    ]

    # Complexity reduced by delegating task execution to the helper
    return await _run_metadata_tasks(tasks, deliverables, exitfirst)

def apply_parity_fixes(descriptions: list, categories: list) -> None:
    """Apply wording and HTML parity fixes for legacy JSON consistency."""
    # TODO: These strings are hard-coded for legacy parity but should be moved to
    # Docserv config files to allow for proper translation and localization.
    legacy_tail = (
        "<p>The default view of this page is the ```Table of Contents``` sorting order. "
        "To search for a particular document, you can narrow down the results using the "
        "```Filter as you type``` option. It dynamically filters the document titles and "
        "descriptions for what you enter.</p>"
    )
    for desc in descriptions:
        if legacy_tail not in desc.description:
            desc.description += legacy_tail
        desc.description = desc.description.replace("& ", "&amp; ")

    for cat in categories:
        for trans in cat.translations:
            trans.title = trans.title.replace("&", "&amp;")


def load_and_validate_documents(
    files: list[Path],
    meta_cache_dir: Path,
    manifest: Manifest
) -> None:
    """Load JSON metadata files and append validated Document models to the manifest."""
    for f in files:
        # Path resolution for nested folders
        actual_file = f if f.is_absolute() else meta_cache_dir / f

        # Skip if it's a directory
        if not actual_file.is_file():
            continue

        stdout.print(f"  | {f.stem}")
        try:
            with actual_file.open(encoding="utf-8") as fh:
                loaded_doc_data = json.load(fh)

            if not loaded_doc_data:
                log.error("Empty metadata file %s", f)
                continue

            try:
                doc_model = Document.model_validate(loaded_doc_data)
            except ValidationError:
                continue
            manifest.documents.append(doc_model)

        except (json.JSONDecodeError, ValidationError, OSError) as e:
            log.error("Error processing metadata file %s: %s", actual_file, e)


def store_productdocset_json(
    context: DocBuildContext,
    doctypes: Sequence[Doctype],
    stitchnode: etree._ElementTree,
) -> None:
    """Collect all JSON files for product/docset and create a single file.

    :param context: DocBuildContext object
    :param doctypes: Sequence of Doctype objects
    :param stitchnode: The stitched XML tree
    """
    env = context.envconfig
    meta_cache_dir = Path(env.paths.meta_cache_dir)

    for doctype, docset, files in collect_files_flat(doctypes, meta_cache_dir):
        product = doctype.product.value

        # Use the docset directly as the version string
        version_str = str(docset)

        productxpath = f"./{doctype.product_xpath_segment()}"
        productnode = stitchnode.find(productxpath)
        docsetxpath = f"./{doctype.docset_xpath_segment(docset)}"
        docsetnode = productnode.find(docsetxpath)

        # 1. Capture and Clean Descriptions/Categories using helper
        descriptions = list(Description.from_xml_node(productnode))
        categories = list(Category.from_xml_node(productnode))
        apply_parity_fixes(descriptions, categories)

        # 2. Initialize Manifest
        manifest = Manifest(
            productname=productnode.find("name").text,
            acronym=(
                productnode.find("acronym").text
                if productnode.find("acronym") is not None
                else product
            ),
            version=version_str,
            lifecycle=docsetnode.attrib.get("lifecycle") or "",
            hide_productname=False,
            descriptions=descriptions,
            categories=categories,
            documents=[],
            archives=[]
        )

        # 3. Load and validate documents using helper
        load_and_validate_documents(files, meta_cache_dir, manifest)

        # 4. Save and export
        jsondir = meta_cache_dir / product
        jsondir.mkdir(parents=True, exist_ok=True)
        jsonfile = jsondir / f"{docset}.json"

        # Exporting with aliases and INCLUDING defaults (dateModified, rank, isGate)
        json_data = manifest.model_dump(by_alias=True)

        with jsonfile.open("w", encoding="utf-8") as jf:
            # ensure_ascii=False ensures raw UTF-8 (e.g., "á" instead of "\u00e1")
            json.dump(json_data, jf, indent=2, ensure_ascii=False)

        stdout.print(f" > Result: {jsonfile}")
        Category.reset_rank()

async def process(
    context: DocBuildContext,
    doctypes: Sequence[Doctype] | None,
    *,
    exitfirst: bool = False,
    skip_repo_update: bool = False,
) -> int:
    """Asynchronous function to process metadata retrieval.

    :param context: The DocBuildContext containing environment configuration.
    :param doctypes: A sequence of Doctype objects to process.
    :param exitfirst: If True, stop processing on the first failure.
    :param skip_repo_update: If True, skip updating Git repositories before processing.
    :raises ValueError: If no envconfig is found or if paths are not
        configured correctly.
    :return: 0 if all files passed validation, 1 if any failures occurred.
    """
    env = context.envconfig
    configdir = Path(env.paths.config_dir).expanduser()
    stdout.print(f"Config path: {configdir}")
    xmlconfigs = tuple(configdir.rglob("[a-z]*.xml"))
    try:
        stitchnode: etree._ElementTree = await create_stitchfile(xmlconfigs)
    except ValueError as e:
        log.warning(e)

    tmp_metadata_dir = env.paths.tmp.tmp_metadata_dir
    # TODO: Is this necessary here?
    tmp_metadata_dir.mkdir(parents=True, exist_ok=True)

    stitchfilename = tmp_metadata_dir / "stitched-metadata.xml"
    stitchfilename.write_text(
        etree.tostring(
            stitchnode,
            pretty_print=True,
            # xml_declaration=True,
            encoding="unicode",
        )  # .decode('utf-8')
    )

    log.info("Stitched metadata XML written to %s", str(stitchfilename))

    # stdout.print(f'Stitch node: {stitchnode.getroot().tag}')
    # stdout.print(f'Deliverables: {len(stitchnode.xpath(".//deliverable"))}')

    if not doctypes:
        doctypes = [Doctype.from_str(DEFAULT_DELIVERABLES)]

    tasks = [
        process_doctype(
            stitchnode,
            context,
            dt,
            exitfirst=exitfirst,
            skip_repo_update=skip_repo_update,
        )
        for dt in doctypes
    ]
    results_per_doctype = await asyncio.gather(*tasks)

    all_failed_deliverables = [
        d for failed_list in results_per_doctype for d in failed_list
    ]

    # Force the merge regardless of processing success
    store_productdocset_json(context, doctypes, stitchnode)

    if all_failed_deliverables:
        console_err.print(f"Found {len(all_failed_deliverables)} failed deliverables:")
        for d in all_failed_deliverables:
            console_err.print(f"- {d.full_id}")
        return 1

    return 0
