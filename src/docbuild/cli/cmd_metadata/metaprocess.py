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
    basedir = Path(basedir)
    task_stream = ((dt, ds) for dt in doctypes for ds in dt.docset)

    for dt, docset in task_stream:
        # SEARCH RECURSIVELY
        all_files = list(basedir.rglob("DC-*"))
        
        # Case-insensitive filtering
        files = [
            f for f in all_files 
            if dt.product.value.lower() in [p.lower() for p in f.parts] 
            and docset.lower() in [p.lower() for p in f.parts]
        ]
        
        print(f"DEBUG: Filtered down to {len(files)} files for {dt.product.value}/{docset}")

        if files:
            yield dt, docset, files


async def process_deliverable(
    context: DocBuildContext,
    deliverable: Deliverable,
    *,
    repo_dir: Path,
    tmp_repo_dir: Path,
    base_cache_dir: Path,
    meta_cache_dir: Path,
    dapstmpl: str,
) -> bool:
    """Process a single deliverable asynchronously.

    This function creates a temporary clone of the deliverable's repository,
    checks out the correct branch, and then executes the DAPS command to
    generate metadata.

    :param context: The DocBuildContext containing environment configuration.
    :param deliverable: The Deliverable object to process.
    :param repo_dir: The permanent repo path taken from the env
         config ``paths.repo_dir``
    :param tmp_repo_dir: The temporary repo path taken from the env
         config ``paths.tmp_repo_dir``
    :param base_cache_dir: The base path of the cache directory taken
         from the env config ``paths.base_cache_dir``
    :param meta_cache_dir: The ath of the metadata directory taken
         from the env config ``paths.meta_cache_dir``
    :param dapstmp: A template string with the daps command and potential
     placeholders
    :return: True if successful, False otherwise.
    :raises ValueError: If required configuration paths are missing.
    """
    log.info("> Processing deliverable: %s", deliverable.full_id)

    # Tell the type-checker envconfig is definitely not None
    if not context.envconfig:
        log.error("Environment configuration is missing.")
        return False

    meta_cache_dir = Path(meta_cache_dir)
    bare_repo_path = repo_dir / deliverable.git.slug
    if not bare_repo_path.is_dir():
        log.error(f"Bare repository not found for {deliverable.git.name} at {bare_repo_path}")
        return False

    outputdir = meta_cache_dir / deliverable.relpath
    outputdir.mkdir(parents=True, exist_ok=True)

    prefix = f"{deliverable.productid}-{deliverable.docsetid}-{deliverable.lang}--{deliverable.dcfile}"
    outputjson = outputdir / deliverable.dcfile

    try:
        async with PersistentOnErrorTemporaryDirectory(
            dir=str(tmp_repo_dir),
            prefix=f"clone-{prefix}_",
        ) as worktree_dir:
            mg = ManagedGitRepo(deliverable.git.url, repo_dir)
            cloned = await mg.clone_bare()
            if not cloned:
                raise RuntimeError(f"Failed to ensure bare repository for {deliverable.full_id}")

            try:
                await mg.create_worktree(worktree_dir, deliverable.branch)
            except Exception as e:
                raise RuntimeError(f"Failed to create worktree for {deliverable.full_id}: {e}")

            dcfile_path = Path(deliverable.subdir) / deliverable.dcfile
            
            # --- CONTAINER LOGIC START ---
            # Safely access container config
            container_image = None
            if hasattr(context.envconfig, 'build') and context.envconfig.build.container:
                container_image = context.envconfig.build.container.container
            
            # Format the internal DAPS command
            raw_daps_cmd = dapstmpl.format(
                builddir=str(worktree_dir),
                dcfile=str(worktree_dir / dcfile_path),
                output=str(outputjson),
            )

            if container_image:
                # Map the project root to /src inside the container
                # to bypass macOS path complexity
                root_cfg = str(context.envconfig.paths.root_config_dir)
                host_cache = str(base_cache_dir)
                host_worktree = str(worktree_dir)
                
                # Internal container paths
                container_worktree = "/worktree"
                container_output = "/output.json"

                cmd = [
                    "docker", "run", "--rm",
                    "-v", f"{host_worktree}:{container_worktree}", # Mount source to /worktree
                    "-v", f"{outputjson}:{container_output}",      # Mount specific file target
                    container_image,
                    "daps", "-vv", "metadata", 
                    "--output", container_output,
                    f"{container_worktree}/{dcfile_path.name}"      # Path inside container
                ]
                log.info("Executing DAPS in container for %s", deliverable.dcfile)
            else:
                cmd = shlex.split(raw_daps_cmd)
            # --- CONTAINER LOGIC END ---

            daps_process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_data, stderr_data = await daps_process.communicate()
            
            if daps_process.returncode != 0:
                log.error("DAPS Error: %s", stderr_data.decode())
                raise RuntimeError(f"DAPS failed for {deliverable.full_id}")

        fmt = deliverable.format
        with edit_json(outputjson) as jsonconfig:
            jsonconfig["docs"][0]["dcfile"] = deliverable.dcfile
            jsonconfig["docs"][0]["format"]["html"] = deliverable.html_path
            if fmt.get("pdf"):
                jsonconfig["docs"][0]["format"]["pdf"] = deliverable.pdf_path
            if fmt.get("single-html"):
                jsonconfig["docs"][0]["format"]["single-html"] = deliverable.singlehtml_path
            if not jsonconfig["docs"][0]["lang"]:
                jsonconfig["docs"][0]["lang"] = deliverable.language

        log.debug("Updated metadata JSON for %s", deliverable.full_id)
        return True

    except Exception as e:
        log.error("Error processing %s: %s", deliverable.full_id, str(e))
        return False


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
    :param doctypes: A tuple of Doctype objects to process.
    :param exitfirst: If True, stop processing on the first failure.
    :return: True if all files passed validation, False otherwise
    """
    # Here you would implement the logic to process the doctypes
    # and create metadata files based on the stitchnode and context.
    # This is a placeholder for the actual implementation.
    # stdout.print(f'Processing doctypes: {doctype}')
    # xpath = doctype.xpath()
    # print("XPath: ", xpath)
    # stdout.print(f'XPath: {doctype.xpath()}', markup=False)

    env = context.envconfig

    repo_dir: Path = env.paths.repo_dir
    base_cache_dir: Path = env.paths.base_cache_dir
    # We retrieve the path.meta_cache_dir and fall back to path.base_cache_dir
    # if not available:
    meta_cache_dir: Path = env.paths.meta_cache_dir
    # Cloned temporary repo:
    tmp_repo_dir: Path = env.paths.tmp_repo_dir

    deliverables: list[Deliverable] = await asyncio.to_thread(
        get_deliverable_from_doctype,
        root,
        doctype,
    )

    if skip_repo_update:  # pragma: no cover
        log.info("Skipping repository %s updates as requested.", repo_dir)
    else:
        await update_repositories(deliverables, repo_dir)

    # stdout.print(f'Found deliverables: {len(deliverables)}')
    dapsmetatmpl = env.build.daps.meta

    coroutines = [
        process_deliverable(
            context,
            deliverable,
            repo_dir=repo_dir,
            tmp_repo_dir=tmp_repo_dir,
            base_cache_dir=base_cache_dir,
            meta_cache_dir=meta_cache_dir,
            dapstmpl=dapsmetatmpl,
        )
        for deliverable in deliverables
    ]

    tasks = [asyncio.create_task(coro) for coro in coroutines]
    failed_deliverables: list[Deliverable] = []

    if exitfirst:
        # Fail-fast behavior
        for task in asyncio.as_completed(tasks):
            success, deliverable = await task
            if not success:
                failed_deliverables.append(deliverable)
                # cancel others...
                for t in tasks:
                    if not t.done():
                        t.cancel()
                # Wait for cancellations to propagate
                await asyncio.gather(*tasks, return_exceptions=True)
                break  # Exit the loop on first failure

    else:
        # Run all and collect all results
        results = await asyncio.gather(*tasks, return_exceptions=True)
        failed_deliverables.extend(
            deliverable
            for deliverable, success in zip(deliverables, results, strict=False)
            if not success
        )

    return failed_deliverables


def store_productdocset_json(
    context: DocBuildContext,
    doctypes: Sequence[Doctype],
    stitchnode: etree._ElementTree,
) -> None:
    """Collect all JSON file for product/docset and create a single file.

    :param context: DocBuildContext object
    :param doctypes: Sequence of Doctype objects
    :param stitchnode: The stitched XML tree
    """
    meta_cache_dir = Path(context.envconfig.paths.meta_cache_dir)

    for doctype, docset, files in collect_files_flat(doctypes, meta_cache_dir):
        product = doctype.product.value
        
        # Version Formatting
        version_str = str(docset)
        if version_str.endswith(".0"): version_str = version_str[:-2]

        productxpath = f"./{doctype.product_xpath_segment()}"
        productnode = stitchnode.find(productxpath)
        docsetxpath = f"./{doctype.docset_xpath_segment(docset)}"
        docsetnode = productnode.find(docsetxpath)
        
        # --- PARITY FIX: Capture and Clean Descriptions ---
        descriptions = list(Description.from_xml_node(productnode))
        legacy_tail = "<p>The default view of this page is the ‘Table of Contents’ sorting order. To search for a particular document, you can narrow down the results using the ‘Filter as you type’ option. It dynamically filters the document titles and descriptions for what you enter.</p>"
        
        for desc in descriptions:
            if legacy_tail not in desc.description:
                desc.description += legacy_tail
            # Match Legacy HTML entities (literal & to &amp;)
            desc.description = desc.description.replace("& ", "&amp; ")

        categories = list(Category.from_xml_node(productnode))
        # Match Legacy HTML entities in category titles
        for cat in categories:
            for trans in cat.translations:
                trans.title = trans.title.replace("&", "&amp;")

        manifest = Manifest(
            productname=productnode.find("name").text,
            acronym=productnode.find("acronym").text if productnode.find("acronym") is not None else product.upper(),
            version=version_str,
            lifecycle=docsetnode.attrib.get("lifecycle") or "",
            hide_productname=False, 
            descriptions=descriptions,
            categories=categories,
            documents=[],
            archives=[]
        )

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
                    continue
                
                doc_model = Document.model_validate(loaded_doc_data)
                manifest.documents.append(doc_model)

            except Exception as e:
                log.error("Error reading metadata file %s: %s", actual_file, e)
                continue

        jsondir = meta_cache_dir / product
        jsondir.mkdir(parents=True, exist_ok=True)
        jsonfile = jsondir / f"{docset}.json"

        # Serialization for parity
        # We use model_dump() + json.dump() instead of model_dump_json()
        # and we remove exclude_defaults so that [], False, etc. ARE written to the file.
        json_data = manifest.model_dump(by_alias=True, exclude_none=True)
        
        # --- CRITICAL: Use json.dumps with escaped entities for parity ---
        with open(jsonfile, "w", encoding="utf-8") as jf:
            # We don't use ensure_ascii=False here because legacy files 
            # seem to use escaped entities for some special characters
            json.dump(json_data, jf, indent=2)

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
    :param doctype: A Doctype object to process.
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
    stitchnode: etree._ElementTree = await create_stitchfile(xmlconfigs)

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
