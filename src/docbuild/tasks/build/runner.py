"""Runner for the build task."""

import asyncio
import logging
import os
from pathlib import Path
import shlex
import tempfile
from typing import Any, Literal

from aiostream import pipe, stream
from lxml import etree  # type: ignore
import yaml

from ...config.app import normalize_runtime_placeholders
from ...models.deliverable import Deliverable
from ...models.doctype import Doctype
from ...utils.display import get_live_manager
from ...utils.shell import run_command
from ...utils.sync import RsyncOptions, rsync
from ..metadata.prebuilt import read_json_ld
from ..metadata.repos import update_repositories
from ..metadata.runner import get_deliverable_from_doctype
from ..portal import parse_portal_config
from ..publish import render_target_suffix
from ..translations import resolve_actual_translations
from ..worktrees import process_with_shared_worktrees
from .llms import clean_and_convert, inject_llms_links

log = logging.getLogger(__name__)


async def process_single_html_file(
    html_file: Path,
    target_dest: Path,
    llms_dest: Path,
    llmstxt_dir: str,
    domain: str,
    url_product: str,
    url_docset: str,
    static_title: str,
    frontmatter_base: dict[str, Any],
) -> str | None:
    """Process a single HTML file: extract metadata, write Markdown with frontmatter, and inject links."""
    if llmstxt_dir in html_file.parts:
        return None
    try:
        # 1. Read HTML content once
        html_content = await asyncio.to_thread(html_file.read_text, encoding="utf-8")
        md_content = await asyncio.to_thread(clean_and_convert, html_content)

        # 2. Extract JSON-LD from already loaded string content (no double disk read)
        ld_data = read_json_ld(html_content)

        dynamic_title = ld_data.get("name", static_title) if ld_data else static_title
        dynamic_desc = ld_data.get("description", "") if ld_data else ""

        rel_path = html_file.relative_to(target_dest)
        base_url = f"{domain}/{url_product}/{url_docset}/html/{rel_path.as_posix()}"

        frontmatter = {"title": dynamic_title}
        if dynamic_desc:
            frontmatter["description"] = dynamic_desc

        frontmatter.update(frontmatter_base)
        frontmatter["source_url"] = base_url

        # Only inject build_date if dateModified is present in JSON-LD
        if ld_data and "dateModified" in ld_data:
            raw_date = ld_data["dateModified"]
            if raw_date:
                frontmatter["build_date"] = raw_date.split("T")[0]

        # Use yaml.safe_dump for secure serialization
        yaml_block = yaml.safe_dump(
            frontmatter, default_flow_style=False, sort_keys=False, allow_unicode=True
        )
        final_md_content = f"---\n{yaml_block}---\n\n{md_content}"

        md_file = llms_dest / rel_path.with_suffix(".md")
        md_file.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(md_file.write_text, final_md_content, encoding="utf-8")

        md_rel_to_html = Path(os.path.relpath(md_file, html_file.parent)).as_posix()
        llms_txt_rel_to_html = Path(os.path.relpath(target_dest / "llms.txt", html_file.parent)).as_posix()

        new_html = await asyncio.to_thread(
            inject_llms_links, html_content, md_rel_to_html, llms_txt_rel_to_html
        )
        await asyncio.to_thread(html_file.write_text, new_html, encoding="utf-8")

        index_entry = Path(os.path.relpath(md_file, target_dest)).as_posix()
        return f"- [{html_file.name}]({index_entry})"
    except Exception as e:
        log.error("Failed processing %s: %s", html_file, e)
        return None


async def generate_llmstxt(
    deliverable: Deliverable,
    target_dest: Path | str,
    build_llmstxt: bool,
    llmstxt_dir: str,
    canonical_domain: str = "https://documentation.suse.com",
) -> None:
    """Generate LLMs text and inject markdown links into HTML files concurrently."""
    if not build_llmstxt or isinstance(target_dest, str):
        return

    try:
        log.info("Generating LLMs text for %s...", deliverable.full_id)
        llms_dest = target_dest / llmstxt_dir
        llms_dest.mkdir(parents=True, exist_ok=True)

        d_xml = getattr(deliverable, "xml", None)
        static_title = getattr(d_xml, "title", deliverable.full_id) if d_xml else deliverable.full_id
        index_lines = [f"# {static_title}", ""]

        categories = list(d_xml.categories() or []) if d_xml and hasattr(d_xml, "categories") else []
        product = getattr(d_xml, "product_name", getattr(d_xml, "product_id", "")) if d_xml else ""
        version = getattr(d_xml, "docset_version", getattr(d_xml, "docset_path", "")) if d_xml else ""
        language = str(getattr(d_xml, "lang", "")) if d_xml else ""

        # Use dictionary comprehension to filter empty keys (reduces C901 complexity)
        raw_attrs = {
            "product": product,
            "version": version,
            "language": language,
            "categories": categories,
        }
        frontmatter_base: dict[str, Any] = {"deliverable_id": deliverable.full_id}
        frontmatter_base.update({k: v for k, v in raw_attrs.items() if v})

        # Only inject 'generator: daps' if this is an actual DAPS build (not a prebuilt)
        if not getattr(deliverable, "is_prebuilt", False):
            frontmatter_base["generator"] = "daps"

        url_product_id = getattr(d_xml, "product_id", "unknown") if d_xml else "unknown"
        if hasattr(deliverable, "make_safe_name"):
            url_product = deliverable.make_safe_name(url_product_id)
        else:
            url_product = url_product_id.replace("/", "_")

        url_docset = getattr(d_xml, "docset_path", "unknown") if d_xml else "unknown"
        domain = canonical_domain.rstrip("/")

        html_files = list(target_dest.rglob("*.html"))

        async def process_file(html_file: Path) -> str | None:
            return await process_single_html_file(
                html_file=html_file,
                target_dest=target_dest,
                llms_dest=llms_dest,
                llmstxt_dir=llmstxt_dir,
                domain=domain,
                url_product=url_product,
                url_docset=url_docset,
                static_title=static_title,
                frontmatter_base=frontmatter_base,
            )

        pipeline = stream.iterate(html_files) | pipe.map(process_file, ordered=False, task_limit=10)

        async with pipeline.stream() as streamer:
            async for result in streamer:
                if result:
                    index_lines.append(result)

        llms_index = target_dest / "llms.txt"
        llms_index.write_text(chr(10).join(index_lines) + chr(10), encoding="utf-8")
        log.info("Finished generating llms.txt for %s", deliverable.full_id)
    except Exception as ex:
        log.error("Failed to generate LLMs text for %s: %s", deliverable.full_id, ex)


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
            args.extend(["--stringparam", f"canonicals.hreflangs={hreflangs}"])
            log.debug("Injecting canonicals.hreflangs=%s", hreflangs)

    log.info("Building %s for %s...", fmt, deliverable.full_id)

    try:
        process = await run_command(args, cwd=cwd)
        if process.returncode == 0:
            log.info("Successfully built %s for %s", fmt, deliverable.full_id)
            log.info(" -> Artifacts stored in: %s", build_dir)
            return True, process.stdout

        log.error("Failed to build %s for %s:\n%s", fmt, deliverable.full_id, process.stderr)
        return False, process.stderr
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
                        await generate_llmstxt(deliverable, target_dest, build_llmstxt, llmstxt_dir)
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
) -> list[Deliverable]:
    """Process a doctype and build its deliverables using grouped aiostream pipelines."""
    deliverables: list[Deliverable] = await asyncio.to_thread(get_deliverable_from_doctype, root, doctype)

    deliverables = [deli for deli in deliverables if deli.xml.is_dc]
    deliverables.sort()

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

    async def build_single(d: Deliverable, worktree_dir: Path) -> tuple[bool, Deliverable]:
        return await process_single_deliverable(
            d,
            worktree_dir,
            tmp_build_base_dir,
            target_base_dir,
            target_dir_dyn,
            daps_tmpls,
            build_llmstxt,
            llmstxt_dir,
            rsync_options=rsync_options,
        )

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
) -> int:
    """Execute the build task pipeline."""
    root = await parse_portal_config(main_portal_config)
    global_semaphore = asyncio.Semaphore(max_workers)

    manager = get_live_manager()
    if manager and hasattr(manager, "init_task"):
        manager.progress.update(manager.init_task, visible=False)

    overall_task = manager.progress.add_task(f"[bold white]Overall Progress ({len(doctypes)} items)", total=len(doctypes)) if manager else None

    tasks = []
    for dt in doctypes:

        async def _wrapped_process(dt: "Doctype" = dt) -> list:
            # Register individual task right before execution so UI stays clean
            dt_ui = str(dt).replace("@unknown", "")
            task_id = manager.progress.add_task(f"[cyan]{dt_ui}", total=100) if manager else None

            if manager and task_id is not None:
                manager.progress.update(task_id, advance=10)

            res = await process_doctype(
                root, dt, repo_dir, tmp_repo_dir, tmp_build_base_dir, target_base_dir, target_dir_dyn,
                max_workers, global_semaphore, daps_tmpls, skip_repo_update=skip_repo_update,
                build_llmstxt=build_llmstxt, llmstxt_dir=llmstxt_dir, rsync_options=rsync_options,
            )

            if manager:
                if task_id is not None:
                    if not res: # Success
                        # Hide successful items to save space
                        manager.progress.update(task_id, visible=False)
                    else: # Failed
                        status = f"[red]{dt_ui} ❌"
                        manager.progress.update(task_id, completed=100, description=status)
                if overall_task is not None:
                    manager.progress.advance(overall_task)
            return res

        tasks.append(asyncio.create_task(_wrapped_process(), name=f"build:{dt}"))
    results_per_doctype = await asyncio.gather(*tasks)

    all_failed = [d for failed_list in results_per_doctype for d in failed_list]

    if all_failed:
        log.error("Build completed with %d failures.", len(all_failed))
        return 1

    log.info("All deliverables built successfully and synced to target!")
    return 0
