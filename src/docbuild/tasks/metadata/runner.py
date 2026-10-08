"""Task orchestration and main entry point for metadata processing."""

import asyncio
from collections.abc import Sequence
import hashlib
import logging
from pathlib import Path

from aiostream import pipe, stream
from lxml import etree  # type: ignore
from rich.console import Console

from docbuild.config.xml.portal import PortalConfig
from docbuild.constants import DEFAULT_DELIVERABLES
from docbuild.models.deliverable import Deliverable
from docbuild.models.doctype import Doctype
from docbuild.models.homepage import Homepage
from docbuild.tasks.portal import parse_portal_config

from .daps import process_deliverable
from .deliverables import get_deliverable_from_doctype
from .manifest import store_productdocset_json
from .repos import update_repositories

log = logging.getLogger(__name__)
stdout = Console()
console_err = Console(stderr=True, style="red")


def get_deliverable_worker_limit(
    max_workers: int, deliverable_count: int
) -> int:
    """Resolve the concurrency limit for deliverable processing.

    :param max_workers: The maximum number of concurrent workers allowed.
    :param deliverable_count: Number of deliverables to process.
    :return: A worker limit between 1 and ``deliverable_count``.
    """
    if deliverable_count <= 0:
        return 1

    return max(1, min(max_workers, deliverable_count))


async def process_doctype(*args: object, **kwargs: object) -> list[Deliverable]:
    """Return an empty list as tasks are now partitioned globally across doctypes."""
    return []


def _gather_build_tasks(
    stitchnode: etree._ElementTree, doctypes: Sequence[Doctype]
) -> list[Deliverable]:
    """Phase 1: Partition tasks and discover dependencies."""
    resolved_doctypes = [dt for doctype in doctypes for dt in doctype.iter_doctypes(stitchnode.getroot())]

    initial_deliverables: list[Deliverable] = []
    for dt in resolved_doctypes:
        initial_deliverables.extend(get_deliverable_from_doctype(stitchnode, dt))

    build_tasks: dict[str, Deliverable] = {}

    for d in initial_deliverables:
        if not d.xml.is_xref:
            build_tasks[d.full_id] = d
        else:
            target = d.xml.final_target_node
            if target is not None and etree.QName(target).localname == "deliverable":
                target_d = Deliverable(_node=target)
                build_tasks[target_d.full_id] = target_d

    return sorted(build_tasks.values())


def _generate_homepage(stitchnode: etree._ElementTree, json_cache_dir: Path) -> None:
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


async def _execute_build_pipeline(
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
) -> list[Deliverable]:
    """Phase 2: Build Task Pipeline (aiostream)."""
    if skip_repo_update:
        log.info("Skipping repository updates as requested.")
    else:
        git_deliverables = [d for d in deliverables_to_build if d.xml.git_remote() is not None]
        await update_repositories(git_deliverables, repo_dir)

    worker_limit = get_deliverable_worker_limit(max_workers, len(deliverables_to_build))

    async def process_deliverable_wrapper(
        deliverable: Deliverable, *args: object
    ) -> tuple[bool, Deliverable]:
        try:
            # The task name will be inherited by all child tasks and logs.
            # This helps to distinguish logs for different deliverables.
            return await asyncio.create_task(
                process_deliverable(
                    deliverable,
                    repo_dir,
                    tmp_repo_dir,
                    meta_cache_dir,
                    prebuilt_dir=prebuilt_dir,
                    dapstmpl=dapsmetatmpl,
                    daps_list_srcfiles_tmpl=daps_list_srcfiles_tmpl,
                    skip_repo_update=skip_repo_update,
                    env_config_hash=env_config_hash,
                ),
                name=f"metadata:{deliverable.full_id}",
            )
        except Exception as e:
            log.error("Error in task for %s: %s", deliverable.full_id, e)
            return False, deliverable

    pipeline = stream.iterate(deliverables_to_build) | pipe.map(
        process_deliverable_wrapper, task_limit=worker_limit, ordered=True
    )

    all_failed_deliverables: list[Deliverable] = []

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

    # Create a hash of the entire stitched configuration to detect env/config changes!
    env_config_hash = hashlib.sha256(stitch_xml_str.encode("utf-8")).hexdigest()

    log.info("Stitched metadata XML written to %s", str(stitchfilename))

    if not doctypes:
        doctypes = [Doctype.from_str(DEFAULT_DELIVERABLES, default_lang="*")]

    # --- Phase 1: Task Partitioning & Dependency Discovery ---
    deliverables_to_build = _gather_build_tasks(stitchnode, doctypes)

    # --- Phase 2: Build Task Pipeline (aiostream) ---
    all_failed_deliverables = await _execute_build_pipeline(
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
    )

    # --- Phase 3: Reference Resolution & Manifest Assembly ---
    await asyncio.to_thread(
        store_productdocset_json,
        doctypes,
        stitchnode,
        meta_cache_dir,
        json_cache_dir,
        full_categories=full_categories,
    )

    await asyncio.to_thread(_generate_homepage, stitchnode, json_cache_dir)

    if all_failed_deliverables:
        console_err.print(f"Found {len(all_failed_deliverables)} failed deliverables:")
        for d in all_failed_deliverables:
            console_err.print(f"- {d.full_id}")
        return 1

    return 0
