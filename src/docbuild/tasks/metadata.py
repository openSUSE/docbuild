"""Tasks for extracting and processing deliverable metadata."""

import asyncio
from collections.abc import Generator, Sequence
import json
import logging
from pathlib import Path
import shlex
from typing import Any

from lxml import etree  # type: ignore
from pydantic import ValidationError
from rich.console import Console

from docbuild.constants import DEFAULT_DELIVERABLES
from docbuild.models.deliverable import Deliverable
from docbuild.models.doctype import Doctype
from docbuild.models.manifest import Category, Description, Document, Manifest
from docbuild.tasks.portal import parse_portal_config
from docbuild.utils.contextmgr import PersistentOnErrorTemporaryDirectory, edit_json
from docbuild.utils.git import ManagedGitRepo

# Set up rich consoles for output
stdout = Console()
console_err = Console(stderr=True, style="red")

# Set up logging
log = logging.getLogger(__name__)


def get_deliverable_from_doctype(
    root: etree._ElementTree,
    doctype: Doctype,
) -> list[Deliverable]:
    """Get deliverable from doctype."""
    languages = root.getroot().xpath(f"./{doctype.xpath()}")

    return [
        Deliverable(node)
        for language in languages
        for node in language.findall("deliverable")
    ]


def collect_files_flat(
    doctypes: Sequence[Doctype],
    basedir: Path,
) -> Generator[tuple[Doctype, str, list[Path]], Any, None]:
    """Recursively collect all DC-metadata files from the cache directory."""
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
        doc["dcfile"] = deliverable.xml.dcfile
        doc["format"]["html"] = deliverable.paths.html_path
        if fmt.get("pdf"):
            doc["format"]["pdf"] = deliverable.paths.pdf_path
        if fmt.get("single-html"):
            doc["format"]["single-html"] = deliverable.paths.singlehtml_path
        if not doc.get("lang"):
            doc["lang"] = deliverable.xml.lang


async def process_deliverable(
    deliverable: Deliverable,
    repo_dir: Path,
    tmp_repo_dir: Path,
    meta_cache_dir: Path,
    dapstmpl: str,
) -> tuple[bool, Deliverable]:
    """Process a single deliverable asynchronously."""
    log.info("> Processing deliverable: %s", deliverable.full_id)

    bare_repo_path = repo_dir / str(deliverable.git.slug)
    if not bare_repo_path.is_dir():
        log.error("Bare repository not found for %s at %s", deliverable.git.name, bare_repo_path)
        return False, deliverable

    outputdir = meta_cache_dir / str(deliverable.paths.relpath or "")
    outputdir.mkdir(parents=True, exist_ok=True)
    outputjson = outputdir / str(deliverable.xml.dcfile or "")

    try:
        async with PersistentOnErrorTemporaryDirectory(
            dir=str(tmp_repo_dir),
            prefix=f"clone-{deliverable.xml.productid}-{deliverable.xml.docsetid}-{deliverable.xml.lang}-{deliverable.xml.dcfile}_",
        ) as worktree_dir:
            mg = ManagedGitRepo(deliverable.git.url, repo_dir)
            if not await mg.clone_bare():
                raise RuntimeError(f"Failed to ensure bare repository for {deliverable.full_id}")

            try:
                await mg.create_worktree(worktree_dir, deliverable.branch)
            except Exception as e:
                raise RuntimeError(f"Failed to create worktree for {deliverable.full_id}: {e}") from e

            full_dcfile_path = Path(worktree_dir) / str(deliverable.subdir or "") / str(deliverable.xml.dcfile or "")

            cmd = get_daps_command(Path(worktree_dir), full_dcfile_path, outputjson, dapstmpl)

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
    """Update all Git repositories associated with the deliverables."""
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
    doctype: Doctype,
    repo_dir: Path,
    tmp_repo_dir: Path,
    meta_cache_dir: Path,
    dapsmetatmpl: str,
    *,
    exitfirst: bool = False,
    skip_repo_update: bool = False,
) -> list[Deliverable]:
    """Process the doctypes and create metadata files."""
    deliverables: list[Deliverable] = await asyncio.to_thread(
        get_deliverable_from_doctype, root, doctype
    )

    if skip_repo_update:
        log.info("Skipping repository %s updates as requested.", repo_dir)
    else:
        await update_repositories(deliverables, repo_dir)

    tasks = [
        asyncio.create_task(
            process_deliverable(d, repo_dir, tmp_repo_dir, meta_cache_dir, dapsmetatmpl)
        )
        for d in deliverables
    ]

    return await _run_metadata_tasks(tasks, deliverables, exitfirst)


def apply_parity_fixes(descriptions: list, categories: list) -> None:
    """Apply wording and HTML parity fixes for legacy JSON consistency."""
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
        actual_file = f if f.is_absolute() else meta_cache_dir / f

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
    doctypes: Sequence[Doctype],
    stitchnode: etree._ElementTree,
    meta_cache_dir: Path,
) -> None:
    """Collect all JSON files for product/docset and create a single file."""
    for doctype, docset, files in collect_files_flat(doctypes, meta_cache_dir):
        product = doctype.product.value
        version_str = str(docset)

        productxpath = f"./{doctype.product_xpath_segment()}"
        productnode = stitchnode.find(productxpath)
        docsetxpath = f"./{doctype.docset_xpath_segment(docset)}"
        docsetnode = productnode.find(docsetxpath)

        descriptions = list(Description.from_xml_node(productnode))
        categories = list(Category.from_xml_node(productnode))
        apply_parity_fixes(descriptions, categories)

        manifest = Manifest(
            productname=productnode.find("name").text,
            acronym=(
                productnode.find("acronym").text
                if productnode.find("acronym") is not None
                else product
            ),
            version=version_str,
            lifecycle=docsetnode.attrib.get("lifecycle") or "",
            hide_productname=False,  # type: ignore[call-arg]
            descriptions=descriptions,
            categories=categories,
            documents=[],
            archives=[]
        )

        load_and_validate_documents(files, meta_cache_dir, manifest)

        jsondir = meta_cache_dir / product
        jsondir.mkdir(parents=True, exist_ok=True)
        jsonfile = jsondir / f"{docset}.json"

        json_data = manifest.model_dump(by_alias=True)

        with jsonfile.open("w", encoding="utf-8") as jf:
            json.dump(json_data, jf, indent=2, ensure_ascii=False)

        stdout.print(f" > Result: {jsonfile}")
        Category.reset_rank()


async def generate_metadata(
    main_portal_config: Path,
    tmp_metadata_dir: Path,
    repo_dir: Path,
    tmp_repo_dir: Path,
    meta_cache_dir: Path,
    dapsmetatmpl: str,
    doctypes: Sequence[Doctype] | None = None,
    *,
    exitfirst: bool = False,
    skip_repo_update: bool = False,
) -> int:
    """Asynchronous task to process metadata retrieval."""
    stitchnode: etree._ElementTree = await parse_portal_config(main_portal_config)

    tmp_metadata_dir.mkdir(parents=True, exist_ok=True)
    stitchfilename = tmp_metadata_dir / "stitched-metadata.xml"
    stitchfilename.write_text(
        etree.tostring(stitchnode, pretty_print=True, encoding="unicode")
    )

    log.info("Stitched metadata XML written to %s", str(stitchfilename))

    if not doctypes:
        doctypes = [Doctype.from_str(DEFAULT_DELIVERABLES)]

    tasks = [
        process_doctype(
            stitchnode,
            dt,
            repo_dir,
            tmp_repo_dir,
            meta_cache_dir,
            dapsmetatmpl,
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
    store_productdocset_json(doctypes, stitchnode, meta_cache_dir)

    if all_failed_deliverables:
        console_err.print(f"Found {len(all_failed_deliverables)} failed deliverables:")
        for d in all_failed_deliverables:
            console_err.print(f"- {d.full_id}")
        return 1

    return 0
