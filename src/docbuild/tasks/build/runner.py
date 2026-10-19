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

from ...cli.console import console
from ...constants import DEFAULT_DELIVERABLES
from ...models.deliverable import Deliverable
from ...models.doctype import Doctype
from ...utils.contextmgr import PersistentOnErrorTemporaryDirectory
from ...utils.git import ManagedGitRepo
from ...utils.shell import run_command
from ...utils.sync import rsync
from ..metadata.prebuilt import find_html_path, read_json_ld
from ..metadata.repos import update_repositories
from ..metadata.runner import get_deliverable_from_doctype, get_deliverable_worker_limit
from ..portal import parse_portal_config
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
    *,
    llms_index_path: Path | None = None,
    rel_path_override: Path | None = None,
    inject_links: bool = True,
) -> str | None:
    """Convert one HTML file to Markdown with YAML frontmatter and link tags.

    Read the HTML file, strip navigation chrome, extract JSON-LD metadata
    when available, write the resulting Markdown file under ``llms_dest``,
    and optionally inject ``<link rel="alternate" type="text/markdown">``
    tags into the original HTML file.

    :param html_file: (Path) Path to the source HTML file to process.
    :param target_dest: (Path) Root HTML target directory for the
        deliverable or docset.
    :param llms_dest: (Path) Destination directory where converted
        Markdown files are written.
    :param llmstxt_dir: (str) Name of the Markdown subdirectory to skip
        if encountered during traversal.
    :param domain: (str) Canonical base domain without a trailing slash.
    :param url_product: (str) URL-safe product identifier segment.
    :param url_docset: (str) Docset path segment for constructing the
        canonical ``source_url``.
    :param static_title: (str) Fallback title used when JSON-LD does not
        define a document name.
    :param frontmatter_base: (dict[str, Any]) Base metadata fields to
        merge into the YAML frontmatter block.
    :param llms_index_path: (Path | None) Optional path to the root
        ``llms.txt`` index file; defaults to ``target_dest / "llms.txt"``.
    :param rel_path_override: (Path | None) Optional relative path for the
        HTML/Markdown file when ``html_file`` is outside ``target_dest``.
    :param inject_links: (bool) Whether to inject alternate link tags into
        ``html_file``.
    :returns: (str | None) A formatted Markdown list item for
        ``llms.txt``, or ``None`` if the file was skipped or failed.
    """
    if llmstxt_dir in html_file.parts:
        return None
    try:
        # 1. Read HTML content once
        html_content = await asyncio.to_thread(html_file.read_text, encoding="utf-8")
        md_content = await asyncio.to_thread(clean_and_convert, html_content)

        # 2. Extract JSON-LD from already loaded string content (no double disk read)
        ld_data = read_json_ld(html_content, source_name=html_file)
        if ld_data:
            console.print(
                f"  [info]Read HTML:[/] {html_file} [success](JSON-LD found)[/]"
            )
        else:
            console.print(
                f"  [info]Read HTML:[/] {html_file} [warning](no JSON-LD found)[/]"
            )

        dynamic_title = ld_data.get("name", static_title) if ld_data else static_title
        dynamic_desc = ld_data.get("description", "") if ld_data else ""

        rel_path = rel_path_override if rel_path_override is not None else html_file.relative_to(target_dest)
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

        effective_llms_index = llms_index_path if llms_index_path is not None else (target_dest / "llms.txt")

        if inject_links:
            md_rel_to_html = Path(os.path.relpath(md_file, html_file.parent)).as_posix()
            llms_txt_rel_to_html = Path(os.path.relpath(effective_llms_index, html_file.parent)).as_posix()

            new_html = await asyncio.to_thread(
                inject_llms_links, html_content, md_rel_to_html, llms_txt_rel_to_html
            )
            await asyncio.to_thread(html_file.write_text, new_html, encoding="utf-8")

        index_entry = Path(os.path.relpath(md_file, effective_llms_index.parent)).as_posix()
        return f"- [{html_file.name}]({index_entry})"
    except Exception as e:
        log.error("Failed processing %s: %s", html_file, e)
        return None


def str_attr(obj: object, *names: str, default: str = "") -> str:
    """Return the first non-empty string attribute from ``obj``, or ``default``."""
    for name in names:
        val = getattr(obj, name, None)
        if isinstance(val, str) and val:
            return val
    return default


def build_frontmatter_context(
    deliverable: Deliverable,
    canonical_domain: str,
) -> tuple[str, dict[str, Any], str, str, str]:
    """Extract static title, base frontmatter dict, and URL parts from a deliverable.

    :param deliverable: (Deliverable) The deliverable supplying metadata.
    :param canonical_domain: (str) Base URL domain.
    :returns: (tuple[str, dict[str, Any], str, str, str]) A tuple of
        ``(static_title, frontmatter_base, domain, url_product, url_docset)``.
    """
    d_xml = getattr(deliverable, "xml", None)
    static_title = (
        str_attr(d_xml, "title", "prebuilt_title", default=deliverable.full_id)
        if d_xml
        else deliverable.full_id
    )

    categories: list[str] = []
    if d_xml:
        raw_cats = getattr(d_xml, "categories", None)
        if isinstance(raw_cats, list):
            categories = [str(c) for c in raw_cats if c]
        elif callable(raw_cats):
            cat_title = str_attr(d_xml, "category_title", "categoryid")
            if cat_title:
                categories = [cat_title]

    product = str_attr(d_xml, "product_name", "productname", "product_id") if d_xml else ""
    version = str_attr(d_xml, "docset_version", "docset_path") if d_xml else ""
    lang_obj = getattr(d_xml, "lang", None) if d_xml else None
    language = (
        str_attr(lang_obj, "language", default=str(lang_obj))
        if lang_obj is not None
        else ""
    )

    raw_attrs = {
        "product": product,
        "version": version,
        "language": language,
        "categories": categories,
    }
    frontmatter_base: dict[str, Any] = {"deliverable_id": deliverable.full_id}
    frontmatter_base.update({k: v for k, v in raw_attrs.items() if v})

    is_prebuilt = getattr(deliverable, "is_prebuilt", False) is True or (
        d_xml is not None and getattr(d_xml, "is_prebuilt", False) is True
    )
    if not is_prebuilt:
        frontmatter_base["generator"] = "daps"

    url_product_id = str_attr(d_xml, "product_id", default="unknown") if d_xml else "unknown"
    make_safe = getattr(Deliverable, "make_safe_name", None)
    url_product = make_safe(url_product_id) if callable(make_safe) else url_product_id.replace("/", "_")

    url_docset = str_attr(d_xml, "docset_path", default="unknown") if d_xml else "unknown"
    domain = canonical_domain.rstrip("/")
    return static_title, frontmatter_base, domain, url_product, url_docset


async def generate_llmstxt(
    deliverable: Deliverable,
    target_dest: Path | str,
    build_llmstxt: bool,
    llmstxt_dir: str,
    canonical_domain: str = "https://documentation.suse.com",
    *,
    llms_dest_override: Path | None = None,
    llms_index_path: Path | None = None,
    write_index: bool = True,
) -> bool:
    """Generate Markdown files and ``llms.txt`` for a target HTML directory.

    Concurrently convert all HTML files under ``target_dest`` to Markdown
    with YAML frontmatter, inject alternate Markdown link tags into the
    HTML files, and write an ``llms.txt`` index.

    :param deliverable: (Deliverable) The deliverable supplying metadata
        for YAML frontmatter and the ``llms.txt`` heading.
    :param target_dest: (Path | str) Target HTML directory containing
        the built or copied HTML files.
    :param build_llmstxt: (bool) Flag controlling whether LLMs generation
        is enabled.
    :param llmstxt_dir: (str) Subdirectory under ``target_dest`` where
        converted Markdown files are stored when ``llms_dest_override``
        is not provided.
    :param canonical_domain: (str) Base URL domain used to build
        ``source_url`` frontmatter entries.
    :param llms_dest_override: (Path | None) Optional explicit directory
        where converted Markdown files are stored.
    :param llms_index_path: (Path | None) Optional explicit path to the
        ``llms.txt`` file.
    :param write_index: (bool) Whether to write ``llms.txt`` at the end
        of processing.
    :returns: (bool) ``True`` if generation succeeded or was skipped,
        ``False`` if an error occurred.
    """
    if not build_llmstxt or isinstance(target_dest, str):
        return True

    try:
        log.info("Generating LLMs text for %s...", deliverable.full_id)
        llms_dest = llms_dest_override if llms_dest_override is not None else (target_dest / llmstxt_dir)
        llms_dest.mkdir(parents=True, exist_ok=True)

        static_title, frontmatter_base, domain, url_product, url_docset = (
            build_frontmatter_context(deliverable, canonical_domain)
        )
        index_lines = [f"# {static_title}", ""]
        effective_index = llms_index_path if llms_index_path is not None else (target_dest / "llms.txt")

        html_files = list(target_dest.rglob("*.html"))

        async def process_file(html_file: Path) -> str | None:
            return await process_single_html_file(
                html_file=html_file,
                target_dest=target_dest,
                llms_dest=llms_dest,
                llmstxt_dir=Path(llmstxt_dir).name,
                domain=domain,
                url_product=url_product,
                url_docset=url_docset,
                static_title=static_title,
                frontmatter_base=frontmatter_base,
                llms_index_path=effective_index,
            )

        pipeline = stream.iterate(html_files) | pipe.map(process_file, ordered=False, task_limit=10)

        async with pipeline.stream() as streamer:
            async for result in streamer:
                if result:
                    index_lines.append(result)

        if write_index:
            effective_index.parent.mkdir(parents=True, exist_ok=True)
            effective_index.write_text(chr(10).join(index_lines) + chr(10), encoding="utf-8")
        log.info("Finished generating llms.txt for %s", deliverable.full_id)
        return True
    except Exception as ex:
        log.error("Failed to generate LLMs text for %s: %s", deliverable.full_id, ex)
        return False


async def build_format(
    deliverable: Deliverable,
    fmt: Literal["html", "pdf", "single-html", "epub"],
    cwd: Path,
    build_dir: Path,
    daps_tmpl: str,
) -> tuple[bool, str]:
    """Execute the DAPS build command for a single deliverable format.

    :param deliverable: (Deliverable) The deliverable to build.
    :param fmt: (Literal["html", "pdf", "single-html", "epub"]) Output
        format to pass to DAPS.
    :param cwd: (Path) Working directory containing the deliverable's
        DC file.
    :param build_dir: (Path) Directory where DAPS writes build artifacts.
    :param daps_tmpl: (str) Command template containing ``{dcfile}``,
        ``{builddir}``, and ``{format}`` placeholders.
    :returns: (tuple[bool, str]) A tuple of ``(success, output)`` where
        ``output`` is stdout on success or stderr/error text on failure.
    :raises AssertionError: If ``deliverable.xml.dcfile`` is ``None``.
    """
    dcfile = deliverable.xml.dcfile
    assert dcfile is not None, "Deliverable must have a DC file."

    cmd_str = daps_tmpl.format(
        dcfile=dcfile,
        builddir=str(build_dir),
        format=fmt,
    )
    args = shlex.split(cmd_str)

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


async def process_deliverable_build(
    deliverable: Deliverable,
    repo_dir: Path,
    tmp_repo_dir: Path,
    tmp_build_base_dir: Path,
    target_base_dir: Path,
    target_dir_dyn: str,
    daps_tmpls: dict[str, str],
    build_llmstxt: bool = True,
    llmstxt_dir: str = "docs",
) -> tuple[bool, Deliverable]:
    """Build all enabled formats for a deliverable and sync them to target.

    Create a temporary Git worktree, run DAPS for each enabled output
    format, sync the build output to the resolved target directory, and
    generate ``llms.txt`` and Markdown files for HTML builds.

    :param deliverable: (Deliverable) The deliverable to build.
    :param repo_dir: (Path) Directory containing bare/permanent Git
        repositories.
    :param tmp_repo_dir: (Path) Base directory for temporary Git
        worktrees.
    :param tmp_build_base_dir: (Path) Base directory for temporary DAPS
        build outputs.
    :param target_base_dir: (Path) Root directory where built
        deliverables are synced.
    :param target_dir_dyn: (str) Dynamic path template for resolving the
        deliverable's subdirectory under ``target_base_dir``.
    :param daps_tmpls: (dict[str, str]) Mapping of format names to DAPS
        command templates.
    :param build_llmstxt: (bool) Whether to generate Markdown and
        ``llms.txt`` files after syncing HTML output.
    :param llmstxt_dir: (str) Subdirectory name for generated Markdown
        files.
    :returns: (tuple[bool, Deliverable]) A tuple indicating whether all
        enabled formats succeeded and the processed deliverable.
    """
    safe_id = deliverable.make_safe_name(deliverable.full_id)
    success = True

    # 1. Create temporary worktree (cleaned up automatically)
    async with PersistentOnErrorTemporaryDirectory(
        dir=tmp_repo_dir,
        prefix=f"wt_{safe_id}_",
    ) as worktree_dir:
        mg = ManagedGitRepo(deliverable.git.url, repo_dir)
        try:
            await mg.create_worktree(worktree_dir, deliverable.branch)
        except Exception as e:
            log.error("Failed to create worktree for %s: %s", deliverable.full_id, e)
            return False, deliverable

        cwd = Path(worktree_dir) / deliverable.subdir if deliverable.subdir else Path(worktree_dir)

        # 2. Build all enabled formats (output persists in tmp_build_base_dir)
        for fmt, is_enabled in deliverable.format.items():
            if is_enabled:
                tmpl = daps_tmpls.get(fmt, "daps -d {{dcfile}} --builddir {{builddir}} {{format}}")

                # Persist the output directory instead of auto-deleting it
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
                    # 3. Resolve placeholders for the target path
                    target_suffix = format_target_suffix(target_dir_dyn, deliverable)

                    # Final destination includes the format (e.g. /target/sles/15/en-us/html)
                    local_target = Path(target_base_dir) / target_suffix / fmt
                    local_target.mkdir(parents=True, exist_ok=True)
                    target_dest = local_target

                    log.debug("Syncing %s result to %s", fmt, target_dest)

                    try:
                        # Sync contents of the build directory to the target destination
                        sync_result = await rsync(deliverable_build_dir, target_dest, content_only=True)
                        if fmt == "html":
                            llms_base_dir = resolve_llms_base_dir(target_base_dir, llmstxt_dir)
                            llms_dest = llms_base_dir / target_suffix
                            llms_index_path = Path(target_base_dir) / "llms.txt"
                            await generate_llmstxt(
                                deliverable,
                                target_dest,
                                build_llmstxt,
                                llmstxt_dir,
                                llms_dest_override=llms_dest,
                                llms_index_path=llms_index_path,
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
    daps_tmpls: dict[str, str],
    *,
    skip_repo_update: bool = False,
    build_llmstxt: bool = True,
    llmstxt_dir: str = "docs",
) -> list[Deliverable]:
    """Resolve and build all DC deliverables matching a single doctype.

    :param root: (etree._ElementTree) Parsed Portal XML configuration
        tree.
    :param doctype: (Doctype) Doctype filter selecting which deliverables
        to build.
    :param repo_dir: (Path) Directory containing permanent Git
        repositories.
    :param tmp_repo_dir: (Path) Base directory for temporary Git
        worktrees.
    :param tmp_build_base_dir: (Path) Base directory for temporary DAPS
        build outputs.
    :param target_base_dir: (Path) Root directory where built
        deliverables are synced.
    :param target_dir_dyn: (str) Dynamic path template for resolving the
        target subdirectory.
    :param max_workers: (int) Maximum number of concurrent deliverable
        builds.
    :param daps_tmpls: (dict[str, str]) Mapping of format names to DAPS
        command templates.
    :param skip_repo_update: (bool) Whether to skip fetching Git
        repository updates before building.
    :param build_llmstxt: (bool) Whether to generate Markdown and
        ``llms.txt`` files for HTML builds.
    :param llmstxt_dir: (str) Subdirectory name for generated Markdown
        files.
    :returns: (list[Deliverable]) List of deliverables whose build or
        sync failed.
    """
    deliverables: list[Deliverable] = await asyncio.to_thread(get_deliverable_from_doctype, root, doctype)

    deliverables = [deli for deli in deliverables if deli.xml.is_dc]
    deliverables.sort()

    if skip_repo_update:
        log.info("Skipping repository updates for %s as requested.", repo_dir)
    else:
        await update_repositories(deliverables, repo_dir)

    worker_limit = get_deliverable_worker_limit(max_workers, len(deliverables))

    async def build_wrapper(d: Deliverable, *args: object) -> tuple[bool, Deliverable]:
        try:
            return await asyncio.create_task(
                process_deliverable_build(
                    d,
                    repo_dir,
                    tmp_repo_dir,
                    tmp_build_base_dir,
                    target_base_dir,
                    target_dir_dyn,
                    daps_tmpls,
                    build_llmstxt,
                    llmstxt_dir,
                ),
                name=f"build:{d.full_id}",
            )
        except Exception as e:
            log.error("Build task error for %s: %s", d.full_id, e)
            return False, d

    pipeline: Any = stream.iterate(deliverables) | pipe.map(
        build_wrapper, task_limit=worker_limit, ordered=True  # type: ignore[arg-type]
    )

    failed: list[Deliverable] = []
    try:
        async with pipeline.stream() as streamer:
            async for success, deliverable in streamer:
                if not success:
                    failed.append(deliverable)
    except Exception as e:
        log.error("Pipeline failed unexpectedly: %s", e)

    return failed


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
) -> int:
    """Execute the asynchronous build pipeline across the given doctypes.

    :param main_portal_config: (Path) Path to the main Portal XML
        configuration file.
    :param repo_dir: (Path) Directory containing permanent Git
        repositories.
    :param tmp_repo_dir: (Path) Base directory for temporary Git
        worktrees.
    :param tmp_build_base_dir: (Path) Base directory for temporary DAPS
        build outputs.
    :param target_base_dir: (Path) Root directory where built
        deliverables are synced.
    :param target_dir_dyn: (str) Dynamic path template for resolving the
        target subdirectory.
    :param max_workers: (int) Maximum number of concurrent deliverable
        builds per doctype.
    :param doctypes: (tuple[Doctype, ...] | list[Doctype]) Doctypes to
        build.
    :param daps_tmpls: (dict[str, str]) Mapping of format names to DAPS
        command templates.
    :param skip_repo_update: (bool) Whether to skip fetching Git
        repository updates before building.
    :param build_llmstxt: (bool) Whether to generate Markdown and
        ``llms.txt`` files for HTML builds.
    :param llmstxt_dir: (str) Subdirectory name for generated Markdown
        files.
    :returns: (int) Exit code ``0`` if all deliverables succeeded, or
        ``1`` if any deliverable failed.
    """
    root = await parse_portal_config(main_portal_config)

    tasks = [
        asyncio.create_task(
            process_doctype(
                root,
                dt,
                repo_dir,
                tmp_repo_dir,
                tmp_build_base_dir,
                target_base_dir,
                target_dir_dyn,
                max_workers,
                daps_tmpls,
                skip_repo_update=skip_repo_update,
                build_llmstxt=build_llmstxt,
                llmstxt_dir=llmstxt_dir,
            ),
            name=f"build:{dt}",
        )
        for dt in doctypes
    ]
    results_per_doctype = await asyncio.gather(*tasks)

    all_failed = [d for failed_list in results_per_doctype for d in failed_list]

    if all_failed:
        log.error("Build completed with %d failures.", len(all_failed))
        return 1

    log.info("All deliverables built successfully and synced to target!")
    return 0


def format_target_suffix(target_dir_dyn: str, deliverable: Deliverable) -> str:
    """Format the dynamic target directory suffix for a deliverable.

    Normalize single- or double-brace placeholders (``{product}`` or
    ``{{product}}``, ``{docset}`` or ``{{docset}}``, ``{lang}`` or
    ``{{lang}}``) and substitute values from ``deliverable.xml``.

    :param target_dir_dyn: (str) Dynamic directory template string.
    :param deliverable: (Deliverable) Deliverable providing
        ``product_id``, ``docset_path``, and ``lang``.
    :returns: (str) Resolved relative path suffix.

    .. code-block:: python

        suffix = format_target_suffix(
            "{{lang}}/{{product}}/{{docset}}",
            deliverable,
        )
        # e.g. "en-us/sles/16.0"
    """
    normalized = (
        target_dir_dyn.replace("{{product}}", "{product}")
        .replace("{{docset}}", "{docset}")
        .replace("{{lang}}", "{lang}")
    )
    return normalized.format(
        product=deliverable.xml.product_id,
        docset=deliverable.xml.docset_path,
        lang=deliverable.xml.lang,
    )


def resolve_prebuilt_rel_path(deliverable: Deliverable, html_url: str) -> Path:
    """Resolve the relative destination path for a prebuilt HTML URL.

    Strip leading ``<product>/<docset>`` or ``<docset>`` segments from
    ``html_url`` when they match the deliverable's ``product_id`` and
    ``docset_path`` so the file can be placed cleanly inside the docset's
    target HTML directory without duplicating those path segments.

    :param deliverable: (Deliverable) Prebuilt deliverable providing
        ``product_id`` and ``docset_path``.
    :param html_url: (str) Relative URL or path from the prebuilt
        deliverable configuration.
    :returns: (Path) Relative file path within the docset's ``html``
        directory.

    .. code-block:: python

        rel = resolve_prebuilt_rel_path(
            deliverable,
            "/cloudnative/rancher-ai/latest/en/introduction.html",
        )
        # PosixPath('latest/en/introduction.html')
    """
    clean_parts = Path(html_url.lstrip("/")).parts
    product_id = deliverable.xml.product_id or ""
    docset_path = deliverable.xml.docset_path or ""

    if (
        len(clean_parts) > 2
        and clean_parts[0] == product_id
        and clean_parts[1] == docset_path
    ):
        return Path(*clean_parts[2:])
    if len(clean_parts) > 1 and clean_parts[0] == docset_path:
        return Path(*clean_parts[1:])
    return Path(*clean_parts)


def resolve_llms_base_dir(target_base_dir: Path, llmstxt_dir: str) -> Path:
    """Resolve the base directory for generated Markdown files.

    If ``llmstxt_dir`` is an absolute path, return it directly; otherwise
    resolve it relative to ``target_base_dir``.

    :param target_base_dir: (Path) Root directory for built deliverables.
    :param llmstxt_dir: (str) Configured Markdown output directory path or
        name.
    :returns: (Path) Resolved base directory for Markdown output.
    """
    configured = Path(llmstxt_dir)
    return configured if configured.is_absolute() else (Path(target_base_dir) / configured)


async def convert_prebuilt_deliverable(
    deliverable: Deliverable,
    prebuilt_dir: Path,
    llms_dest: Path,
    llms_index_path: Path,
    llmstxt_dir: str,
    canonical_domain: str = "https://documentation.suse.com",
) -> str | None:
    """Convert one prebuilt deliverable's HTML file in ``prebuilt_dir`` to Markdown.

    Locate the prebuilt HTML file in ``prebuilt_dir``, convert it to
    Markdown under ``llms_dest`` without copying or modifying the HTML
    file, and return its ``llms.txt`` index entry.

    :param deliverable: (Deliverable) The prebuilt deliverable to convert.
    :param prebuilt_dir: (Path) Base directory containing prebuilt HTML
        trees.
    :param llms_dest: (Path) Destination directory under ``llmstxt_dir``
        where the converted Markdown file is written.
    :param llms_index_path: (Path) Path to the ``llms.txt`` index file.
    :param llmstxt_dir: (str) Configured Markdown directory name.
    :param canonical_domain: (str) Base URL domain used to construct
        ``source_url`` metadata.
    :returns: (str | None) The formatted ``llms.txt`` list entry, or
        ``None`` if the HTML file was not found or conversion failed.
    """
    html_url = deliverable.xml.resolved_prebuilt_html_url or deliverable.xml.prebuilt_html_url
    if not html_url:
        log.warning("Prebuilt deliverable %s has no HTML URL; skipping.", deliverable.full_id)
        return None

    html_path = await asyncio.to_thread(find_html_path, prebuilt_dir, deliverable, html_url)
    if html_path is None:
        log.warning(
            "Prebuilt HTML file not found in %s for %s (%s); skipping.",
            prebuilt_dir,
            deliverable.full_id,
            html_url,
        )
        return None

    rel_file = resolve_prebuilt_rel_path(deliverable, html_url)
    static_title, frontmatter_base, domain, url_product, url_docset = (
        build_frontmatter_context(deliverable, canonical_domain)
    )

    return await process_single_html_file(
        html_file=html_path,
        target_dest=prebuilt_dir,
        llms_dest=llms_dest,
        llmstxt_dir=Path(llmstxt_dir).name,
        domain=domain,
        url_product=url_product,
        url_docset=url_docset,
        static_title=static_title,
        frontmatter_base=frontmatter_base,
        llms_index_path=llms_index_path,
        rel_path_override=rel_file,
        inject_links=False,
    )


async def process_deliverable_llms(
    deliverable: Deliverable,
    target_base_dir: Path,
    target_dir_dyn: str,
    prebuilt_dir: Path,
    build_llmstxt: bool,
    llmstxt_dir: str,
    canonical_domain: str = "https://documentation.suse.com",
) -> bool:
    """Generate LLMs Markdown files for one deliverable under ``target_base_dir / llmstxt_dir``.

    Resolve the deliverable's Markdown destination under
    ``<target_base_dir>/<llmstxt_dir>/<target_suffix>`` and convert its
    HTML files from ``target_base_dir`` (for DAPS builds) or
    ``prebuilt_dir`` (for prebuilt deliverables).

    :param deliverable: (Deliverable) The deliverable to process.
    :param target_base_dir: (Path) Root directory for built deliverables.
    :param target_dir_dyn: (str) Dynamic path template for resolving the
        deliverable's subdirectory under ``target_base_dir``.
    :param prebuilt_dir: (Path) Base directory containing prebuilt HTML
        deliverables.
    :param build_llmstxt: (bool) Flag enabling LLMs file generation.
    :param llmstxt_dir: (str) Directory name (relative to
        ``target_base_dir``) or absolute path for generated Markdown files.
    :param canonical_domain: (str) Base URL domain used to construct
        ``source_url`` metadata.
    :returns: (bool) ``True`` if processing succeeded, ``False`` if the
        target HTML directory or prebuilt source was missing or failed.
    """
    target_suffix = format_target_suffix(target_dir_dyn, deliverable)
    llms_base_dir = resolve_llms_base_dir(target_base_dir, llmstxt_dir)
    llms_dest = llms_base_dir / target_suffix
    llms_index_path = Path(target_base_dir) / "llms.txt"

    if deliverable.xml.is_prebuilt:
        html_url = deliverable.xml.resolved_prebuilt_html_url or deliverable.xml.prebuilt_html_url
        if not html_url:
            log.warning("Prebuilt deliverable %s has no HTML URL; skipping.", deliverable.full_id)
            return True
        entry = await convert_prebuilt_deliverable(
            deliverable=deliverable,
            prebuilt_dir=prebuilt_dir,
            llms_dest=llms_dest,
            llms_index_path=llms_index_path,
            llmstxt_dir=llmstxt_dir,
            canonical_domain=canonical_domain,
        )
        return entry is not None

    target_dest = Path(target_base_dir) / target_suffix / "html"
    if not target_dest.exists() or not target_dest.is_dir():
        log.warning(
            "Target HTML directory does not exist for %s at %s; skipping.",
            deliverable.full_id,
            target_dest,
        )
        return False

    return await generate_llmstxt(
        deliverable=deliverable,
        target_dest=target_dest,
        build_llmstxt=build_llmstxt,
        llmstxt_dir=llmstxt_dir,
        canonical_domain=canonical_domain,
        llms_dest_override=llms_dest,
        llms_index_path=llms_index_path,
        write_index=False,
    )


async def process_prebuilt_group_llms(
    llms_dest: Path,
    llms_index_path: Path,
    group: list[Deliverable],
    prebuilt_dir: Path,
    build_llmstxt: bool,
    llmstxt_dir: str,
    canonical_domain: str = "https://documentation.suse.com",
) -> bool:
    """Convert prebuilt HTML files for a docset group into Markdown under ``llms_dest``.

    :param llms_dest: (Path) Shared Markdown destination directory for the
        docset group under ``<target_base_dir>/<llmstxt_dir>/<target_suffix>``.
    :param llms_index_path: (Path) Path to the root ``llms.txt`` index file.
    :param group: (list[Deliverable]) Prebuilt deliverables belonging to
        the same docset.
    :param prebuilt_dir: (Path) Base directory containing prebuilt HTML
        deliverables.
    :param build_llmstxt: (bool) Flag enabling LLMs file generation.
    :param llmstxt_dir: (str) Subdirectory name for generated Markdown
        files.
    :param canonical_domain: (str) Base URL domain used to construct
        ``source_url`` metadata.
    :returns: (bool) ``True`` if at least one prebuilt HTML file was
        converted, ``False`` otherwise.
    """
    if not build_llmstxt:
        return True

    converted_any = False
    log.info("Generating LLMs text for %s...", group[0].full_id)
    for d in group:
        entry = await convert_prebuilt_deliverable(
            deliverable=d,
            prebuilt_dir=prebuilt_dir,
            llms_dest=llms_dest,
            llms_index_path=llms_index_path,
            llmstxt_dir=llmstxt_dir,
            canonical_domain=canonical_domain,
        )
        if entry is not None:
            converted_any = True

    if converted_any:
        log.info("Finished generating LLMs Markdown for %s", group[0].full_id)
    return converted_any


def write_root_llmstxt_index(
    target_base_dir: Path,
    llms_base_dir: Path,
    llms_index_path: Path,
) -> None:
    """Write the root ``llms.txt`` index listing all generated Markdown files under ``llms_base_dir``.

    :param target_base_dir: (Path) Root target directory.
    :param llms_base_dir: (Path) Directory containing generated ``.md`` files.
    :param llms_index_path: (Path) Path where ``llms.txt`` is written.
    :returns: (None)
    """
    if not llms_base_dir.exists():
        return

    md_files = sorted(llms_base_dir.rglob("*.md"))
    if not md_files:
        return

    index_lines = [f"# Documentation Index for {target_base_dir.name}", ""]
    for md_file in md_files:
        rel_entry = Path(os.path.relpath(md_file, llms_index_path.parent)).as_posix()
        index_lines.append(f"- [{md_file.stem}.html]({rel_entry})")

    llms_index_path.parent.mkdir(parents=True, exist_ok=True)
    llms_index_path.write_text(chr(10).join(index_lines) + chr(10), encoding="utf-8")


def partition_llms_deliverables(
    eligible: list[Deliverable],
    target_base_dir: Path,
    target_dir_dyn: str,
) -> tuple[list[Deliverable], dict[str, list[Deliverable]]]:
    """Partition deliverables into DC items and grouped prebuilt target suffixes.

    Deduplicate DC deliverables that resolve to the same target suffix so
    each docset directory is scanned once, and group prebuilt deliverables
    by their resolved ``target_suffix``.

    :param eligible: (list[Deliverable]) HTML-enabled DC and prebuilt
        deliverables matching the requested doctypes.
    :param target_base_dir: (Path) Root directory for built deliverables.
    :param target_dir_dyn: (str) Dynamic path template for resolving each
        deliverable's subdirectory under ``target_base_dir``.
    :returns: (tuple[list[Deliverable], dict[str, list[Deliverable]]])
        A tuple of ``(dc_deliverables, prebuilt_groups)``.

    .. code-block:: python

        dc_list, pb_groups = partition_llms_deliverables(
            eligible,
            Path("/srv/docs"),
            "{lang}/{product}/{docset}",
        )
    """
    _ = target_base_dir
    seen_targets: set[str] = set()
    dc_deliverables: list[Deliverable] = []
    prebuilt_groups: dict[str, list[Deliverable]] = {}

    for d in eligible:
        target_suffix = format_target_suffix(target_dir_dyn, d)
        if d.xml.is_prebuilt:
            prebuilt_groups.setdefault(target_suffix, []).append(d)
        elif target_suffix not in seen_targets:
            seen_targets.add(target_suffix)
            dc_deliverables.append(d)

    return dc_deliverables, prebuilt_groups


async def process_llms(
    main_portal_config: Path,
    target_base_dir: Path,
    target_dir_dyn: str,
    prebuilt_dir: Path,
    build_llmstxt: bool,
    llmstxt_dir: str,
    doctypes: tuple[Doctype, ...] | list[Doctype] | None = None,
    canonical_domain: str = "https://documentation.suse.com",
) -> int:
    """Generate Markdown and ``llms.txt`` files across matching deliverables.

    Parse the Portal XML configuration, resolve the requested ``doctypes``
    (or default to all deliverables when ``doctypes`` is ``None`` or
    empty), partition matching HTML deliverables into DC and prebuilt
    groups, write Markdown files under ``<target_base_dir>/<llmstxt_dir>/<target_suffix>``,
    and write the root ``<target_base_dir>/llms.txt`` index.

    :param main_portal_config: (Path) Path to the main Portal XML
        configuration file.
    :param target_base_dir: (Path) Root directory containing built HTML
        deliverables and receiving generated LLMs files.
    :param target_dir_dyn: (str) Dynamic path template for resolving the
        target subdirectory per deliverable.
    :param prebuilt_dir: (Path) Base directory containing prebuilt HTML
        deliverables.
    :param build_llmstxt: (bool) Flag enabling LLMs file generation;
        returns ``0`` immediately when ``False``.
    :param llmstxt_dir: (str) Subdirectory name relative to
        ``target_base_dir`` (or absolute path) where Markdown files are
        written.
    :param doctypes: (tuple[Doctype, ...] | list[Doctype] | None)
        Optional doctype filters; defaults to all deliverables when
        ``None`` or empty.
    :param canonical_domain: (str) Base URL domain used to construct
        ``source_url`` frontmatter values.
    :returns: (int) Exit code ``0`` if all processed deliverables
        succeeded, or ``1`` if the portal configuration is missing or any
        deliverable failed.

    .. code-block:: python

        exit_code = await process_llms(
            main_portal_config=Path("/etc/docbuild/portal.xml"),
            target_base_dir=Path("/srv/docs/target"),
            target_dir_dyn="{lang}/{product}/{docset}",
            prebuilt_dir=Path("/srv/docs/prebuilt"),
            build_llmstxt=True,
            llmstxt_dir="docs",
            doctypes=[Doctype.from_str("sles/16.0/en-us")],
        )
    """
    if not build_llmstxt:
        return 0

    if not main_portal_config.exists():
        log.error("Main portal config not found: %s", main_portal_config)
        return 1

    root = await parse_portal_config(Path(main_portal_config).expanduser())

    if not doctypes:
        doctypes = [Doctype.from_str(DEFAULT_DELIVERABLES, default_lang="*")]

    resolved_doctypes = [
        dt for doctype in doctypes for dt in doctype.iter_doctypes(root.getroot())
    ]

    eligible = [
        d
        for dt in resolved_doctypes
        for d in get_deliverable_from_doctype(root, dt)
        if (d.xml.is_dc or d.xml.is_prebuilt) and d.format.get("html", False)
    ]

    if not eligible:
        log.warning("No deliverables found for the selected doctypes.")
        return 0

    dc_deliverables, prebuilt_groups = partition_llms_deliverables(
        eligible, target_base_dir, target_dir_dyn
    )
    llms_base_dir = resolve_llms_base_dir(target_base_dir, llmstxt_dir)
    llms_index_path = Path(target_base_dir) / "llms.txt"

    dc_results = [
        await process_deliverable_llms(
            deliverable=d,
            target_base_dir=target_base_dir,
            target_dir_dyn=target_dir_dyn,
            prebuilt_dir=prebuilt_dir,
            build_llmstxt=build_llmstxt,
            llmstxt_dir=llmstxt_dir,
            canonical_domain=canonical_domain,
        )
        for d in dc_deliverables
    ]

    pb_results = [
        await process_prebuilt_group_llms(
            llms_dest=llms_base_dir / target_suffix,
            llms_index_path=llms_index_path,
            group=group,
            prebuilt_dir=prebuilt_dir,
            build_llmstxt=build_llmstxt,
            llmstxt_dir=llmstxt_dir,
            canonical_domain=canonical_domain,
        )
        for target_suffix, group in prebuilt_groups.items()
    ]

    await asyncio.to_thread(
        write_root_llmstxt_index, target_base_dir, llms_base_dir, llms_index_path
    )

    return 0 if all(dc_results) and all(pb_results) else 1
