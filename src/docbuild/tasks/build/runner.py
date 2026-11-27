"""Runner for the build task."""

import asyncio
from contextlib import nullcontext
import logging
from pathlib import Path
import shlex
import tempfile
from typing import Literal

from lxml import etree  # type: ignore

from docbuild.tasks.build.llms.generator import generate_llmstxt

from ...config.app import normalize_runtime_placeholders
from ...models.deliverable import Deliverable
from ...models.doctype import Doctype
from ...utils.display import get_live_manager
from ...utils.shell import run_command
from ...utils.sync import RsyncOptions, rsync
from ..metadata.repos import update_repositories
from ..metadata.runner import get_deliverable_from_doctype
from ..portal import parse_portal_config
from ..publish import render_target_suffix
from ..translations import resolve_actual_translations
from ..worktrees import process_with_shared_worktrees

log = logging.getLogger(__name__)


async def build_format(
    deliverable: Deliverable,
    fmt: Literal["html", "pdf", "single-html", "epub"],
    cwd: Path,
    build_dir: Path,
    daps_tmpl: str,
) -> tuple[bool, str]:
    """Execute the DAPS build command dynamically from a config template."""
    dcfile = deliverable.xml.dcfile
    assert dcfile is not None, "Deliverable must have a DC file."

    cmd_str = normalize_runtime_placeholders(daps_tmpl).format(
        dcfile=dcfile,
        builddir=str(build_dir),
        format=fmt,
    )
    args = shlex.split(cmd_str)

    # Inject canonicals and hreflangs for HTML outputs via DAPS
    if args and args[0] == "daps" and fmt in ("html", "single-html"):
        translations = getattr(deliverable, "resolved_translations", deliverable.xml.translations)
        if translations:
            hreflangs = " ".join(sorted(translations))
            args.extend(["--stringparam", shlex.quote(f"canonicals.hreflangs={hreflangs}")])
            log.debug("Injecting canonicals.hreflangs=%s", hreflangs)

    log.info("Building %s for %s...", fmt, deliverable.full_id)

    try:
        process = await run_command(args, cwd=cwd)
        if process.returncode == 0:
            log.info("Successfully built %s for %s", fmt, deliverable.full_id)
            log.info(" -> Artifacts stored in: %s", build_dir)
            return True, process.stdout

        output = "\n".join(
            text for text in (process.stdout, process.stderr) if text
        ) or "No output captured."
        log.error(
            "Failed to build %s for %s (exit code %s):\n%s",
            fmt,
            deliverable.full_id,
            process.returncode,
            output,
        )
        return False, output
    except Exception as e:
        log.error("Error executing daps for %s: %s", deliverable.full_id, e)
        return False, str(e)


async def process_single_deliverable(
    deliverable: Deliverable,
    worktree_dir: Path,
    tmp_build_base_dir: Path,
    target_base_dir: Path,
    target_dir_dyn: str,
    daps_tmpls: dict[str, str],
    build_llmstxt: bool = True,
    llmstxt_dir: str = "docs",
    rsync_options: RsyncOptions | None = None,
    llms_exclude: list[str] | None = None,
    llms_exclude_extra: list[str] | None = None,
) -> tuple[bool, Deliverable]:
    """Build and sync formats for a single deliverable using an existing worktree."""
    safe_id = deliverable.make_safe_name(deliverable.full_id)
    success = True
    cwd = worktree_dir / deliverable.subdir if deliverable.subdir else worktree_dir

    for fmt, is_enabled in deliverable.format.items():
        if is_enabled:
            # Fixed string formatting template (removed double braces)
            tmpl = daps_tmpls.get(fmt, "daps -d {dcfile} --builddir {builddir} {format}")

            deliverable_build_dir = Path(
                tempfile.mkdtemp(
                    dir=tmp_build_base_dir,
                    prefix=f"build_{safe_id}_",
                    suffix=f"_{fmt}",
                )
            )

            fmt_success, _ = await build_format(deliverable, fmt, cwd, deliverable_build_dir, tmpl)

            if not fmt_success:
                success = False
            else:
                # Resolve placeholders for the target path using upstream's normalize_runtime_placeholders
                target_suffix = render_target_suffix(target_dir_dyn, deliverable)
                local_target = Path(target_base_dir) / target_suffix / fmt
                local_target.mkdir(parents=True, exist_ok=True)
                target_dest = local_target

                log.debug("Syncing %s result to %s", fmt, target_dest)

                try:
                    # Sync contents of the build directory to the target destination
                    sync_result = await rsync(
                        deliverable_build_dir,
                        target_dest,
                        content_only=True,
                        options=rsync_options,
                    )
                    if fmt == "html":
                        await generate_llmstxt(
                            deliverable=deliverable,
                            target_base_dir=target_base_dir,
                            build_llmstxt=build_llmstxt,
                            llmstxt_dir=llmstxt_dir,
                            html_dir=target_dest,
                            llms_exclude=llms_exclude,
                            llms_exclude_extra=llms_exclude_extra,
                        )
                    if sync_result.returncode == 0:
                        log.info("Successfully synced %s for %s", fmt, deliverable.full_id)
                    else:
                        log.error(
                            "Failed to sync %s for %s to %s:\n%s",
                            fmt,
                            deliverable.full_id,
                            target_dest,
                            sync_result.stderr,
                        )
                        success = False
                except Exception as e:
                    log.error("Exception occurred while syncing %s for %s: %s", fmt, deliverable.full_id, e)
                    success = False

    return success, deliverable


async def process_doctype(
    root: etree._ElementTree,
    doctype: Doctype,
    repo_dir: Path,
    tmp_repo_dir: Path,
    tmp_build_base_dir: Path,
    target_base_dir: Path,
    target_dir_dyn: str,
    max_workers: int,
    semaphore: asyncio.Semaphore,
    daps_tmpls: dict[str, str],
    *,
    skip_repo_update: bool = False,
    build_llmstxt: bool = True,
    llmstxt_dir: str = "docs",
    rsync_options: RsyncOptions | None = None,
    llms_exclude: list[str] | None = None,
    llms_exclude_extra: list[str] | None = None,
) -> list[Deliverable]:
    """Process a doctype and build its deliverables using grouped aiostream pipelines."""
    deliverables: list[Deliverable] = await asyncio.to_thread(get_deliverable_from_doctype, root, doctype)

    deliverables = [deli for deli in deliverables if deli.xml.is_dc]
    deliverables.sort()

    manager = get_live_manager()
    stage = manager._active if manager else None
    if stage is not None and deliverables:
        current_total = stage._total or 0
        stage.set_total(current_total + len(deliverables))

    if skip_repo_update:
        log.info("Skipping repository updates for %s as requested.", repo_dir)
    else:
        await update_repositories(deliverables, repo_dir)

    # Pre-resolve valid translations across all languages for these deliverables
    if deliverables:
        translations_map = await resolve_actual_translations(root, doctype, repo_dir)
        for d in deliverables:
            key = getattr(d.xml, "target_id", None) or getattr(d.xml, "dcfile", None)
            if key and key in translations_map:
                d.resolved_translations = translations_map[key]
            else:
                d.resolved_translations = {str(getattr(d.xml, "lang", "en-us"))}

    manager = get_live_manager()
    stage = manager._active if manager else None

    async def build_single(d: Deliverable, worktree_dir: Path) -> tuple[bool, Deliverable]:
        item_ctx = stage.item(d.full_id) if stage else nullcontext()
        with item_ctx as item:
            try:
                success, deliverable = await process_single_deliverable(
                    d,
                    worktree_dir,
                    tmp_build_base_dir,
                    target_base_dir,
                    target_dir_dyn,
                    daps_tmpls,
                    build_llmstxt,
                    llmstxt_dir,
                    rsync_options=rsync_options,
                    llms_exclude=llms_exclude,
                    llms_exclude_extra=llms_exclude_extra,
                )
                if item and not success:
                    item.fail()
                return success, deliverable
            except Exception:
                if item:
                    item.fail()
                raise

    return await process_with_shared_worktrees(
        deliverables, repo_dir, tmp_repo_dir, max_workers, semaphore, build_single
    )


async def process(
    main_portal_config: Path,
    repo_dir: Path,
    tmp_repo_dir: Path,
    tmp_build_base_dir: Path,
    target_base_dir: Path,
    target_dir_dyn: str,
    max_workers: int,
    doctypes: tuple[Doctype, ...] | list[Doctype],
    daps_tmpls: dict[str, str],
    *,
    skip_repo_update: bool = False,
    build_llmstxt: bool = True,
    llmstxt_dir: str = "docs",
    rsync_options: RsyncOptions | None = None,
    llms_exclude: list[str] | None = None,
    llms_exclude_extra: list[str] | None = None,
) -> int:
    """Execute the build task pipeline."""
    root = await parse_portal_config(main_portal_config)
    global_semaphore = asyncio.Semaphore(max_workers)

    manager = get_live_manager()
    stage_context = (
        manager.stage("3/4 Building deliverables…", total=sum(len(dt.deliverables) for dt in doctypes if getattr(dt, "deliverables", [])) or 1)
        if manager is not None
        else nullcontext()
    )

    with stage_context as stage:
        if stage is not None:
            stage.set_total(0)

        async def _wrapped_process(dt: "Doctype") -> list:
            return await process_doctype(
                root,
                dt,
                repo_dir,
                tmp_repo_dir,
                tmp_build_base_dir,
                target_base_dir,
                target_dir_dyn,
                max_workers,
                global_semaphore,
                daps_tmpls,
                skip_repo_update=skip_repo_update,
                build_llmstxt=build_llmstxt,
                llmstxt_dir=llmstxt_dir,
                rsync_options=rsync_options,
                llms_exclude=llms_exclude,
                llms_exclude_extra=llms_exclude_extra,
            )

        async with asyncio.TaskGroup() as task_group:
            tasks = [
                task_group.create_task(
                    _wrapped_process(dt), name=f"build:{dt}"
                )
                for dt in doctypes
            ]

    results_per_doctype = [task.result() for task in tasks]

    all_failed = [d for failed_list in results_per_doctype for d in failed_list]

    if all_failed:
        log.error("Build completed with %d failures.", len(all_failed))
        return 1

    log.info("All deliverables built successfully and synced to target!")
    return 0
