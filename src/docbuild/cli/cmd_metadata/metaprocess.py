"""Defines the handling of metadata extraction from deliverables."""

import asyncio
from collections.abc import Generator, Sequence
from contextlib import suppress
import json
import logging
import os
from pathlib import Path
import shlex
import tempfile
from typing import Any

from lxml import etree
from pydantic import ValidationError
from rich.console import Console

from ...constants import DEFAULT_DELIVERABLES
from ...models.deliverable import Deliverable
from ...models.doctype import Doctype
from ...models.manifest import Category, Description, Document, Manifest
from ...utils.concurrency import TaskFailedError, run_parallel
from ...utils.contextmgr import PersistentOnErrorTemporaryDirectory, edit_json
from ...utils.git import ManagedGitRepo
from ..cmd_portal.process import parse_portal_config
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
    if not basedir.is_dir():
        return

    langs = [lang.language.lower() for dt in doctypes for lang in dt.langs]
    langs_all = "*" in langs

    task_stream = ((dt, ds) for dt in doctypes for ds in dt.docset)
    for dt, docset in task_stream:
        lang_dirs = [d for d in basedir.iterdir() if d.is_dir()]
        if not langs_all:
            lang_dirs = [d for d in lang_dirs if d.name.lower() in langs]

        files: list[Path] = []
        for lang_dir in lang_dirs:
            product_dir = lang_dir / dt.product.value
            if not product_dir.is_dir():
                continue

            if docset == "*":
                docset_dirs = [d for d in product_dir.iterdir() if d.is_dir()]
            else:
                candidate = product_dir / docset
                docset_dirs = [candidate] if candidate.is_dir() else []

            for docset_dir in docset_dirs:
                files.extend(docset_dir.rglob("DC-*"))

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

    outputdir = meta_cache_dir / deliverable.paths.relpath
    outputdir.mkdir(parents=True, exist_ok=True)
    outputjson = outputdir / deliverable.xml.dcfile

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

            # Use absolute path within worktree to avoid DAPS "Missing DC-file" error
            full_dcfile_path = Path(worktree_dir) / deliverable.subdir / deliverable.xml.dcfile

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
    deliverables: list[Deliverable],
    bare_repo_dir: Path,
    limit: int,
) -> bool:
    """Update all Git repositories associated with the deliverables.

    :param deliverables: A list of Deliverable objects.
    :param bare_repo_dir: The root directory for storing permanent bare clones.
    :param limit: Maximum number of concurrent Git operations.
    """
    log.info("Updating Git repositories...")
    unique_urls = {d.git.url for d in deliverables}
    repos = [ManagedGitRepo(url, bare_repo_dir) for url in unique_urls]

    async def _clone(repo: ManagedGitRepo) -> tuple[ManagedGitRepo, bool]:
        return repo, await repo.clone_bare()

    res = True
    async for result in run_parallel(repos, _clone, limit=limit):
        if isinstance(result, TaskFailedError):
            log.error(
                "Failed to update repository %s: %s",
                result.item.slug,
                result.original_exception,
            )
            res = False
        else:
            repo, success = result
            if not success:
                log.error("Failed to update repository %s", repo.slug)
                res = False

    return res

async def process_doctype(
    root: etree._ElementTree,
    context: DocBuildContext,
    doctype: Doctype,
    *,
    exitfirst: bool = False,
    skip_repo_update: bool = False,
) -> tuple[list[Deliverable], list[Deliverable]]:
    """Process the doctypes and create metadata files.

    :param root: The stitched XML node containing configuration.
    :param context: The DocBuildContext containing environment configuration.
    :param doctype: The Doctype object to process.
    :param exitfirst: If True, stop processing on the first failure.
    :param skip_repo_update: If True, do not fetch updates for the git repositories.
    :return: A tuple of (succeeded Deliverables, failed Deliverables).
    """
    env = context.envconfig
    repo_dir: Path = env.paths.repo_dir

    deliverables: list[Deliverable] = await asyncio.to_thread(
        get_deliverable_from_doctype, root, doctype
    )

    limit: int = context.appconfig.max_workers if context.appconfig.max_workers else 1

    if skip_repo_update:
        log.info("Skipping repository %s updates as requested.", repo_dir)
    else:
        await update_repositories(deliverables, repo_dir, limit=limit)

    dapsmetatmpl = env.build.daps.meta

    async def _process_one(deliverable: Deliverable) -> tuple[bool, Deliverable]:
        success = await process_deliverable(context, deliverable, dapstmpl=dapsmetatmpl)
        return success, deliverable

    succeeded: list[Deliverable] = []
    failed: list[Deliverable] = []

    async for result in run_parallel(deliverables, _process_one, limit=limit):
        if isinstance(result, TaskFailedError):
            log.error("Task failed unexpectedly for %s: %s (id=%s)", result.item.full_id, result.original_exception, result.item.xml.id)
            failed.append(result.item)
            if exitfirst:
                break
        else:
            success, deliverable = result
            if success:
                succeeded.append(deliverable)
            else:
                failed.append(deliverable)
                if exitfirst:
                    break

    # If exitfirst triggered and not all deliverables were processed,
    # append remaining items to the failed list.
    processed_ids = {d.full_id for d in succeeded + failed}
    for deliverable in deliverables:
        if deliverable.full_id not in processed_ids:
            failed.append(deliverable)

    return succeeded, failed


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
    manifest: Manifest,
    static_deliverables: dict[tuple[str, str, str, str], Deliverable] | None = None,
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

            file_identity = _extract_file_identity(actual_file, meta_cache_dir)
            static_deliverable = None
            if file_identity and static_deliverables:
                static_deliverable = static_deliverables.get(file_identity)

            loaded_doc_data = _merge_dynamic_document_data(
                loaded_doc_data,
                file_identity=file_identity,
                static_deliverable=static_deliverable,
            )

            try:
                doc_model = Document.model_validate(loaded_doc_data)
            except ValidationError:
                continue
            manifest.documents.append(doc_model)

        except (json.JSONDecodeError, ValidationError, OSError) as e:
            log.error("Error processing metadata file %s: %s", actual_file, e)


def _extract_file_identity(
    actual_file: Path,
    meta_cache_dir: Path,
) -> tuple[str, str, str, str] | None:
    """Extract language/product/docset/dcfile identity from a metadata file path."""
    try:
        rel = actual_file.relative_to(meta_cache_dir)
    except ValueError:
        return None

    if len(rel.parts) < 4:
        return None

    language, product, docset = rel.parts[:3]
    dcfile = actual_file.name
    return language, product, docset, dcfile


def _merge_dynamic_document_data(
    loaded_doc_data: dict[str, Any],
    *,
    file_identity: tuple[str, str, str, str] | None,
    static_deliverable: Deliverable | None,
) -> dict[str, Any]:
    """Merge dynamic JSON data with static XML-derived defaults."""
    docs = loaded_doc_data.get("docs")
    if not isinstance(docs, list):
        return loaded_doc_data

    for single_doc in docs:
        if isinstance(single_doc, dict):
            _merge_single_document_entry(
                single_doc,
                file_identity=file_identity,
                static_deliverable=static_deliverable,
            )

    return loaded_doc_data


def _merge_single_document_entry(
    single_doc: dict[str, Any],
    *,
    file_identity: tuple[str, str, str, str] | None,
    static_deliverable: Deliverable | None,
) -> None:
    """Merge identity and format defaults into a single doc dictionary."""
    _apply_identity_defaults(single_doc, file_identity, static_deliverable)
    _apply_static_format_defaults(single_doc, static_deliverable)


def _apply_identity_defaults(
    single_doc: dict[str, Any],
    file_identity: tuple[str, str, str, str] | None,
    static_deliverable: Deliverable | None,
) -> None:
    """Apply identity defaults such as date, dcfile, and language."""
    language = file_identity[0] if file_identity else ""
    dcfile = file_identity[3] if file_identity else ""

    if "datemodified" not in single_doc and single_doc.get("dateModified"):
        single_doc["datemodified"] = single_doc["dateModified"]

    if not single_doc.get("dcfile"):
        single_doc["dcfile"] = dcfile or _static_dcfile(static_deliverable)

    if not single_doc.get("lang") and language:
        single_doc["lang"] = language


def _static_dcfile(static_deliverable: Deliverable | None) -> str:
    """Return static dcfile or empty string."""
    if static_deliverable is None or not static_deliverable.xml.dcfile:
        return ""
    return static_deliverable.xml.dcfile


def _apply_static_format_defaults(
    single_doc: dict[str, Any],
    static_deliverable: Deliverable | None,
) -> None:
    """Apply static format defaults to a document entry when available."""
    if static_deliverable is None:
        return

    fmt = single_doc.get("format")
    if not isinstance(fmt, dict):
        fmt = {}

    fmt.setdefault("html", static_deliverable.paths.html_path)
    if static_deliverable.format.get("pdf"):
        fmt.setdefault("pdf", static_deliverable.paths.pdf_path)
    if static_deliverable.format.get("single-html"):
        fmt.setdefault("single-html", static_deliverable.paths.singlehtml_path)

    single_doc["format"] = fmt


def _build_static_deliverable_index(
    portalnode: etree._ElementTree,
    doctypes: Sequence[Doctype],
) -> dict[tuple[str, str, str, str], Deliverable]:
    """Build an index of static deliverables keyed by path-like identity."""
    static_deliverables: dict[tuple[str, str, str, str], Deliverable] = {}

    for doctype in doctypes:
        for deliverable in get_deliverable_from_doctype(portalnode, doctype):
            if not deliverable.xml.docsetid or not deliverable.xml.dcfile:
                continue

            key = (
                str(deliverable.xml.lang),
                deliverable.xml.productid,
                deliverable.xml.docsetid,
                deliverable.xml.dcfile,
            )
            static_deliverables[key] = deliverable

    return static_deliverables


def _collect_docset_file_groups(
    doctypes: Sequence[Doctype],
    meta_cache_dir: Path,
) -> dict[tuple[str, str], list[Path]]:
    """Group metadata files by language/product/docset under meta cache."""
    grouped: dict[tuple[str, str], list[Path]] = {}

    for doctype, _docset, files in collect_files_flat(doctypes, meta_cache_dir):
        allowed_langs = {lang.language for lang in doctype.langs}
        for file_path in files:
            try:
                rel = file_path.relative_to(meta_cache_dir)
            except ValueError:
                continue

            if len(rel.parts) < 4:
                continue

            language, product, docset = rel.parts[:3]
            if "*" not in allowed_langs and language not in allowed_langs:
                continue

            key = (product, docset)
            grouped.setdefault(key, []).append(file_path)

    for key, values in grouped.items():
        grouped[key] = sorted(set(values))

    return grouped


def _write_manifest_json_file(jsonfile: Path, json_data: dict[str, Any]) -> None:
    """Write a JSON file atomically to avoid partial writes."""
    jsonfile.parent.mkdir(parents=True, exist_ok=True)
    tmp_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=str(jsonfile.parent),
            delete=False,
            prefix=f".{jsonfile.stem}.",
            suffix=".tmp",
        ) as tmp_file:
            tmp_path = Path(tmp_file.name)
            json.dump(json_data, tmp_file, indent=2, ensure_ascii=False)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())

        with suppress(FileNotFoundError):
            tmp_path.chmod(jsonfile.stat().st_mode)

        tmp_path.replace(jsonfile)

        with suppress(OSError):
            dir_fd = os.open(str(jsonfile.parent), os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)

        tmp_path = None
    finally:
        if tmp_path and tmp_path.exists():
            with suppress(OSError):
                tmp_path.unlink()


def _resolve_product_docset_nodes(
    portalnode: etree._ElementTree,
    product: str,
    docset: str,
) -> tuple[etree._Element | None, etree._Element | None]:
    """Resolve product and docset nodes from stitched portal XML."""
    productnode = portalnode.find(f"./product[@productid={product!r}]")
    if productnode is None:
        productnode = portalnode.find(f"./product[@id={product!r}]")

    if productnode is None:
        return None, None

    docsetnode = productnode.find(f"./docset[@setid={docset!r}]")
    if docsetnode is None:
        docsetnode = productnode.find(f"./docset[@path={docset!r}]")

    return productnode, docsetnode


async def _store_docset_json_file(
    meta_cache_dir: Path,
    json_cache_dir: Path,
    category_lock: asyncio.Lock,
    group_key: tuple[str, str],
    deliverables: list[Deliverable],
) -> None:
    """Aggregate one product/docset group into a single JSON file."""
    product, docset = group_key

    rep = deliverables[0]

    # Category rank is shared state; lock this section for deterministic output.
    async with category_lock:
        descriptions = list(Description.from_xml_node(rep))
        categories = list(Category.from_xml_node(rep))
        apply_parity_fixes(descriptions, categories)

        name_node = rep.xml.product_node.find("name")
        acronym_node = rep.xml.product_node.find("acronym")

        manifest = Manifest(
            productname=name_node.text if name_node is not None and name_node.text else product,
            acronym=(
                acronym_node.text
                if acronym_node is not None and acronym_node.text
                else product
            ),
            version=str(docset),
            lifecycle=rep.xml.docset_node.attrib.get("lifecycle") or "",
            hide_productname=False,
            descriptions=descriptions,
            categories=categories,
            documents=[],
            archives=[],
        )
        Category.reset_rank()

    files = []
    static_index = {}

    for d in deliverables:
        file_identity = (str(d.xml.lang), d.xml.productid, d.xml.docsetid, d.xml.dcfile)
        static_index[file_identity] = d

        actual_file = meta_cache_dir / d.paths.relpath / d.xml.dcfile
        files.append(actual_file)

    await asyncio.to_thread(
        load_and_validate_documents,
        files,
        meta_cache_dir,
        manifest,
        static_index,
    )

    output_file = json_cache_dir / product / f"{docset}.json"
    json_data = manifest.model_dump(by_alias=True)
    await asyncio.to_thread(_write_manifest_json_file, output_file, json_data)

    stdout.print(f" > Result: {output_file}")


async def store_productdocset_json(
    context: DocBuildContext,
    deliverables: Sequence[Deliverable],
) -> None:
    """Collect JSON files for the provided deliverables and create aggregate files."""
    if not deliverables:
        return

    env = context.envconfig
    meta_cache_dir = env.paths.meta_cache_dir
    json_cache_dir = env.paths.json_cache_dir

    grouped_deliverables: dict[tuple[str, str], list[Deliverable]] = {}
    for d in deliverables:
        if d.xml.productid and d.xml.docsetid:
            grouped_deliverables.setdefault((d.xml.productid, d.xml.docsetid), []).append(d)

    category_lock = asyncio.Lock()
    limit: int = context.appconfig.max_workers if context.appconfig.max_workers else 1

    async def _run_store(group_items: tuple[tuple[str, str], list[Deliverable]]):
        key, group = group_items
        return await _store_docset_json_file(
            meta_cache_dir,
            json_cache_dir,
            category_lock,
            key,
            group,
        )

    async for result in run_parallel(list(sorted(grouped_deliverables.items())), _run_store, limit=limit):
        if isinstance(result, TaskFailedError):
            log.error("Failed to store Docset JSON: %s", result.original_exception)


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
    main_portal_config = Path(env.paths.main_portal_config).expanduser()
    stdout.print(f"Config path: {configdir}")
    portalnode: etree._ElementTree = await parse_portal_config(main_portal_config)

    tmp_metadata_dir = env.paths.tmp.tmp_metadata_dir
    # TODO: Is this necessary here?
    tmp_metadata_dir.mkdir(parents=True, exist_ok=True)

    portalxml = tmp_metadata_dir / "stitched-metadata.xml"
    portalxml.write_text(
        etree.tostring(
            portalnode,
            pretty_print=True,
            # xml_declaration=True,
            encoding="unicode",
        )  # .decode('utf-8')
    )

    log.info("Stitched metadata XML written to %s", str(portalxml))

    # stdout.print(f'Stitch node: {portalnode.getroot().tag}')
    # stdout.print(f'Deliverables: {len(portalnode.xpath(".//deliverable"))}')

    if not doctypes:
        doctypes = [Doctype.from_str(DEFAULT_DELIVERABLES)]

    all_succeeded_deliverables: list[Deliverable] = []
    all_failed_deliverables: list[Deliverable] = []
    for dt in doctypes:
        succeeded, failed = await process_doctype(
            portalnode,
            context,
            dt,
            exitfirst=exitfirst,
            skip_repo_update=skip_repo_update,
        )
        all_succeeded_deliverables.extend(succeeded)
        all_failed_deliverables.extend(failed)
        if exitfirst and failed:
            break

    # 2. Force the merge regardless of processing success
    await store_productdocset_json(context, all_succeeded_deliverables)

    if all_failed_deliverables:
        console_err.print(f"Found {len(all_failed_deliverables)} failed deliverables:")
        for d in all_failed_deliverables:
            console_err.print(f"- {d.full_id}")
        return 1

    return 0
