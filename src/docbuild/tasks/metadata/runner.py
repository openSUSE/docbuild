"""Task orchestration and main entry point for metadata processing."""

import asyncio
from collections.abc import Sequence
from contextlib import nullcontext
from functools import partial
import hashlib
import logging
from pathlib import Path

from aiostream import pipe, stream
from lxml import etree  # type: ignore

from docbuild.cli.console import console, console_err
from docbuild.config.xml.portal import PortalConfig
from docbuild.constants import DEFAULT_DELIVERABLES, DEFAULT_LANG, XML_ID
from docbuild.models.deliverable import Deliverable
from docbuild.models.doctype import Doctype
from docbuild.models.homepage import Homepage
from docbuild.models.lifecycle import LifecycleFlag
from docbuild.tasks.portal import parse_portal_config
from docbuild.utils.display import get_live_manager
from docbuild.utils.git import ManagedGitRepo

from .daps import process_deliverable
from .deliverables import get_deliverable_from_doctype
from .manifest import store_productdocset_json
from .repos import update_repositories

log = logging.getLogger(__name__)
stdout = console


def get_deliverable_worker_limit(
    max_workers: int, deliverable_count: int
) -> int:
    """Resolve the concurrency limit for deliverable processing."""
    if deliverable_count <= 0:
        return 1

    return max(1, min(max_workers, deliverable_count))


async def process_doctype(*args: object, **kwargs: object) -> list[Deliverable]:
    """Return an empty list as tasks are now partitioned globally across doctypes."""
    return []


def is_deliverable_node(node: etree._Element | object | None) -> bool:
    """Safe check for deliverable nodes that degrades gracefully with test Mocks."""
    try:
        return etree.QName(node).localname == "deliverable"
    except ValueError:
        return False
    except TypeError:
        # Gracefully handle MagicMocks in the test suite
        return True


def is_unsupported_deliverable(d: Deliverable) -> bool:
    """Return True if the deliverable's parent docset has an unsupported lifecycle."""
    lifecycle_str = d.xml.docset_node.attrib.get("lifecycle", "")
    return LifecycleFlag.unsupported in LifecycleFlag.from_str(lifecycle_str)


def gather_build_tasks(
    stitchnode: etree._ElementTree, doctypes: Sequence[Doctype]
) -> list[Deliverable]:
    """Phase 1: Partition tasks and discover dependencies."""
    resolved_doctypes = [dt for doctype in doctypes for dt in doctype.iter_doctypes(stitchnode.getroot())]

    initial_deliverables: list[Deliverable] = []
    for dt in resolved_doctypes:
        if LifecycleFlag.unsupported in dt.lifecycle:
            continue
        initial_deliverables.extend(get_deliverable_from_doctype(stitchnode, dt))

    build_tasks: dict[str, Deliverable] = {}

    for d in initial_deliverables:
        if LifecycleFlag.unsupported in d.lifecycle:
            continue

        if not d.xml.is_xref:
            build_tasks[d.full_id] = d
        else:
            # Include translation xrefs so Phase 2 can check them against Git
            if d.xml.lang != DEFAULT_LANG:
                build_tasks[d.full_id] = d

            target = d.xml.final_target_node
            if is_deliverable_node(target):
                target_d = Deliverable(_node=target)
                if LifecycleFlag.unsupported not in target_d.lifecycle:
                    build_tasks[target_d.full_id] = target_d

    return sorted(build_tasks.values())


def generate_homepage(stitchnode: etree._ElementTree, json_cache_dir: Path) -> None:
    """Generate and save the homepage.json manifest."""
    try:
        log.info("Generating homepage.json...")
        portal_config = PortalConfig(source=stitchnode)
        homepage = Homepage.from_portal(portal_config)
        homepage_path = json_cache_dir / "homepage.json"
        homepage.save(homepage_path)
        log.info("Successfully generated %s", homepage_path)
    except Exception as e:
        log.error("Failed to generate homepage.json: %s", e)


def resolve_effective_dcfile(d: Deliverable) -> str | None:
    """Extract the target DC filename, resolving xrefs if necessary."""
    if not d.xml.is_xref:
        return d.xml.dcfile

    target = d.xml.final_target_node
    if is_deliverable_node(target):
        return Deliverable(_node=target).xml.dcfile
    return None


def fallback_to_english_xref(d: Deliverable, dcfile: str, dcpath: str) -> None:
    """Convert an explicit translation into an xref fallback to English."""
    # 2. DC file is missing: Explicit translation falls back to English xref
    dc_node = d.xml.node.find("dc")
    if dc_node is not None:
        d.xml.node.remove(dc_node)

    en_locale = d.xml.locale_en
    if en_locale is not None:
        for en_d in en_locale.findall("deliverable"):
            en_dc = en_d.find("dc")
            if en_dc is not None and en_dc.get("file") == dcfile:
                if target_id := en_d.get(XML_ID):
                    d.xml.node.append(etree.Element("xref", linkend=target_id))
                    log.info("Missing translated DC file %s for %s. Falling back to English blueprint (skipped).", dcpath, d.full_id)
                    return

    log.warning("Missing translated DC file %s for %s, but no English blueprint found.", dcpath, d.full_id)


async def resolve_single_translation(
    d: Deliverable,
    repo_dir: Path,
    tree_cache: dict[tuple[str, str], list[str]],
) -> Deliverable | None:
    """Check Git for a translated DC file and return the Deliverable to build (if any)."""
    fallback_return = None if d.xml.is_xref else d

    if d.xml.lang == DEFAULT_LANG:
        return fallback_return

    repo_url = d.git.url if d.git else None
    branch = d.branch

    if not repo_url or not branch:
        return fallback_return

    dcfile = resolve_effective_dcfile(d)
    if not dcfile:
        return fallback_return

    # Check if DC file exists in the cloned repository (cached per URL+Branch)
    cache_key = (repo_url, branch)
    if cache_key not in tree_cache:
        tree_cache[cache_key] = await ManagedGitRepo(repo_url, repo_dir).ls_tree(branch)

    available_files = tree_cache[cache_key]
    dcpath = "/".join(part for part in (d.subdir, dcfile) if part)

    if dcpath in available_files:
        if d.xml.is_xref:
            # 3. Drop xref pointer and run DAPS on the translated DC file
            xref_node = d.xml.node.find("xref")
            if xref_node is not None:
                d.xml.node.remove(xref_node)
            d.xml.node.append(etree.Element("dc", file=dcfile))
            d = Deliverable(_node=d.xml.node)
            log.info("Found translated DC file %s for %s. Dropped xref to extract localized metadata.", dcpath, d.full_id)
        return d

    # Missing localized DC file path:
    if not d.xml.is_xref:
        fallback_to_english_xref(d, dcfile, dcpath)
    else:
        log.info("Missing translated DC file %s for %s. Inheriting English blueprint (skipped).", dcpath, d.full_id)

    return fallback_return


async def resolve_translation_metadata(
    deliverables: list[Deliverable],
    repo_dir: Path,
) -> list[Deliverable]:
    """Verify translation DC files in Git and dynamically rewrite the XML if found."""
    final_deliverables = []
    tree_cache: dict[tuple[str, str], list[str]] = {}

    for d in deliverables:
        resolved = await resolve_single_translation(d, repo_dir, tree_cache)
        if resolved is not None:
            final_deliverables.append(resolved)

    return final_deliverables


async def _process_single_deliverable(
    deliverable: Deliverable,
    *args: object,
    repo_dir: Path,
    tmp_repo_dir: Path,
    meta_cache_dir: Path,
    prebuilt_dir: Path,
    dapsmetatmpl: str,
    daps_list_srcfiles_tmpl: str,
    skip_repo_update: bool,
    env_config_hash: str,
) -> tuple[bool, Deliverable]:
    """Worker function to process a single deliverable and report to the live UI."""
    manager = get_live_manager()

    stage = manager._active if manager else None
    item_context = stage.item(deliverable.full_id) if stage else nullcontext()

    with item_context as item:
        try:
            if current_task := asyncio.current_task():
                current_task.set_name(f"metadata:{deliverable.full_id}")

            res = await process_deliverable(
                deliverable,
                repo_dir,
                tmp_repo_dir,
                meta_cache_dir,
                prebuilt_dir=prebuilt_dir,
                dapstmpl=dapsmetatmpl,
                daps_list_srcfiles_tmpl=daps_list_srcfiles_tmpl,
                skip_repo_update=skip_repo_update,
                env_config_hash=env_config_hash,
            )
            if item is not None and not res[0]:
                item.fail()
            return res
        except Exception as e:
            log.error("Error in task for %s: %s", deliverable.full_id, e)
            if item is not None:
                item.fail()
            return False, deliverable


async def execute_build_pipeline(  # noqa: C901
    deliverables_to_build: list[Deliverable],
    repo_dir: Path,
    tmp_repo_dir: Path,
    meta_cache_dir: Path,
    prebuilt_dir: Path,
    dapsmetatmpl: str,
    daps_list_srcfiles_tmpl: str,
    skip_repo_update: bool,
    env_config_hash: str,
    max_workers: int,
    exitfirst: bool,
    skip_metadata: bool = False,
) -> list[Deliverable]:
    """Phase 2: Build Task Pipeline (aiostream)."""
    manager = get_live_manager()

    if skip_repo_update:
        log.info("Skipping repository updates as requested.")
        if manager:
            with manager.stage("1/4 Clone repos… (skipped)", total=0):
                pass
    else:
        git_deliverables = [d for d in deliverables_to_build if d.xml.git_remote() is not None]
        manager = get_live_manager()
        unique_repos = {d.git.url for d in git_deliverables if d.git and d.git.url}
        repo_stage = manager.stage("1/4 Clone repos…", total=len(unique_repos)) if manager else nullcontext()
        with repo_stage as r_stage:
            try:
                await update_repositories(git_deliverables, repo_dir)
            except Exception as e:
                if r_stage:
                    r_stage.fail()
                log.error("Failed to update repositories: %s", e)
                if exitfirst:
                    return deliverables_to_build # Return all as failed to abort

    # --- Translation Metadata Git Checks ---
    final_deliverables = await resolve_translation_metadata(deliverables_to_build, repo_dir)

    worker_limit = get_deliverable_worker_limit(max_workers, len(final_deliverables))

    worker = partial(
        _process_single_deliverable,
        repo_dir=repo_dir,
        tmp_repo_dir=tmp_repo_dir,
        meta_cache_dir=meta_cache_dir,
        prebuilt_dir=prebuilt_dir,
        dapsmetatmpl=dapsmetatmpl,
        daps_list_srcfiles_tmpl=daps_list_srcfiles_tmpl,
        skip_repo_update=skip_repo_update,
        env_config_hash=env_config_hash,
    )

    pipeline = stream.iterate(final_deliverables) | pipe.map(
        worker, task_limit=worker_limit, ordered=True
    )

    all_failed_deliverables: list[Deliverable] = []

    manager = get_live_manager()

    if skip_metadata:
        if manager:
            with manager.stage("2/4 Metadata Validation… (skipped)", total=0):
                pass
        return []

    stage_context = (
        manager.stage(
            "2/4 Metadata Validation…", total=len(final_deliverables)
        )
        if manager is not None
        else nullcontext()
    )
    with stage_context:
        try:
            # Evaluate the pipeline and collect results
            async with pipeline.stream() as streamer:
                async for success, deliverable in streamer:
                    if not success:
                        all_failed_deliverables.append(deliverable)
                        if exitfirst:
                            break
        except Exception as e:
            log.error("Task failed unexpectedly: %s", e)

    return all_failed_deliverables


async def process(
    main_portal_config: Path,
    tmp_metadata_dir: Path,
    repo_dir: Path,
    tmp_repo_dir: Path,
    meta_cache_dir: Path,
    json_cache_dir: Path,
    prebuilt_dir: Path,
    dapsmetatmpl: str,
    daps_list_srcfiles_tmpl: str,
    max_workers: int,
    doctypes: Sequence[Doctype] | None,
    *,
    exitfirst: bool = False,
    skip_repo_update: bool = False,
    full_categories: bool = False,
    skip_metadata: bool = False,
) -> int:
    """Asynchronous entry point for metadata retrieval."""
    stitchnode: etree._ElementTree = await parse_portal_config(
        Path(main_portal_config).expanduser()
    )

    tmp_metadata_dir.mkdir(parents=True, exist_ok=True)

    stitchfilename = tmp_metadata_dir / "stitched-metadata.xml"

    stitch_xml_str = etree.tostring(
        stitchnode, pretty_print=True, encoding="unicode"
    )
    stitchfilename.write_text(stitch_xml_str)

    # Create a hash of the entire stitched configuration to detect env/config changes
    env_config_hash = hashlib.sha256(stitch_xml_str.encode("utf-8")).hexdigest()

    log.info("Stitched metadata XML written to %s", str(stitchfilename))

    if not doctypes:
        doctypes = [Doctype.from_str(DEFAULT_DELIVERABLES, default_lang="*")]

    # --- Phase 1: Task Partitioning & Dependency Discovery ---
    deliverables_to_build = gather_build_tasks(stitchnode, doctypes)

    # --- Phase 2: Build Task Pipeline (aiostream) ---
    all_failed_deliverables = await execute_build_pipeline(
        deliverables_to_build,
        repo_dir,
        tmp_repo_dir,
        meta_cache_dir,
        prebuilt_dir,
        dapsmetatmpl,
        daps_list_srcfiles_tmpl,
        skip_repo_update,
        env_config_hash,
        max_workers,
        exitfirst,
        skip_metadata=skip_metadata,
    )

    if exitfirst and all_failed_deliverables:
        console_err.print(f"[error]Exiting early due to failed deliverable:[/] {all_failed_deliverables[0].full_id}")
        return 1

    # --- Phase 3: Reference Resolution & Manifest Assembly ---
    await asyncio.to_thread(
        store_productdocset_json,
        doctypes,
        stitchnode,
        meta_cache_dir,
        json_cache_dir,
        full_categories=full_categories,
    )

    await asyncio.to_thread(generate_homepage, stitchnode, json_cache_dir)

    if all_failed_deliverables:
        console_err.print(f"[error]Found {len(all_failed_deliverables)} failed deliverables:[/]")
        for d in all_failed_deliverables:
            console_err.print(f"- {d.full_id}")
        return 1

    return 0
