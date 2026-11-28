"""Task module for publishing built documentation to a remote destination."""

import asyncio
from collections.abc import Iterable
from contextlib import nullcontext
from dataclasses import replace
import logging
from pathlib import Path
import tempfile

from ..config.app import normalize_runtime_placeholders
from ..models.deliverable import Deliverable
from ..models.doctype import Doctype
from ..utils.display import get_live_manager
from ..utils.sync import RsyncOptions, rsync
from .metadata.runner import get_deliverable_from_doctype
from .portal import parse_portal_config

log = logging.getLogger(__name__)


def render_target_suffix(target_dir_dyn: str, deliverable: Deliverable) -> Path:
    """Render the relative target directory path for a deliverable using template placeholders."""
    rendered = normalize_runtime_placeholders(target_dir_dyn).format(
        product=deliverable.xml.product_id,
        docset=deliverable.xml.docset_path,
        lang=deliverable.xml.lang,
    )
    return Path(rendered)


async def stage_server_root_files(
    server_rootfiles_dir: Path,
    target_base_dir: Path,
    rsync_options: RsyncOptions | None = None,
) -> bool:
    """Stage server root files into the local target base directory.

    :return: False if the source directory does not exist, True on success.
    :raises RuntimeError: If rsync fails to copy the files.
    """
    if not server_rootfiles_dir.is_dir():
        log.warning(
            "Server root files directory does not exist: %s. Skipping staging.",
            server_rootfiles_dir,
        )
        return False

    log.info("Staging server root files from %s to %s...", server_rootfiles_dir, target_base_dir)
    target_base_dir.mkdir(parents=True, exist_ok=True)
    res = await rsync(server_rootfiles_dir, target_base_dir, content_only=True, options=rsync_options)
    if res.returncode != 0:
        msg = f"Failed to stage server root files with returncode {res.returncode}: {res.stderr}"
        log.error(msg)
        raise RuntimeError(msg)
    return True


def _deliverable_publish_paths(
    deliverables: Iterable[Deliverable], target_base_dir: Path, target_dir_dyn: str
) -> set[str]:
    """Find existing output directories for the selected deliverables."""
    paths = set()
    for d in deliverables:
        if not d.xml.is_dc:
            continue
        target_suffix = render_target_suffix(target_dir_dyn, d)
        for fmt, enabled in d.format.items():
            rel_dir = target_suffix / fmt
            if enabled and (target_base_dir / rel_dir).exists():
                paths.add(rel_dir.as_posix())
    return paths


async def collect_publish_paths(
    portal_config: Path,
    doctypes: tuple[Doctype, ...] | list[Doctype],
    target_base_dir: Path,
    target_dir_dyn: str,
    include_server_files: bool = True,
    server_rootfiles_dir: Path | None = None,
) -> list[str]:
    """Collect relative file and directory paths under target_base_dir to publish."""
    paths_to_sync: set[str] = set()
    manager = get_live_manager()
    root_files = server_rootfiles_dir if include_server_files else None
    total = 1 + len(doctypes) + int(root_files is not None)
    stage_ctx = (
        manager.stage("Collect publish paths", total) if manager else nullcontext()
    )
    with stage_ctx as stage:
        with stage.item(f"Parsing {portal_config.name}") if stage else nullcontext():
            root = await parse_portal_config(portal_config)

        for dt in doctypes:
            with stage.item(str(dt)) if stage else nullcontext() as item:
                deliverables = await asyncio.to_thread(
                    get_deliverable_from_doctype, root, dt
                )
                paths = _deliverable_publish_paths(
                    deliverables, target_base_dir, target_dir_dyn
                )
                paths_to_sync.update(paths)
                if item and not paths:
                    item.skip()

        if root_files is not None:
            with stage.item("Server root files") if stage else nullcontext() as item:
                files = (
                    {p.name for p in root_files.iterdir()}
                    if root_files.is_dir()
                    else set()
                )
                paths_to_sync.update(files)
                if item and not files:
                    item.skip()

    return sorted(paths_to_sync)


async def publish_deliverables(
    target_base_dir: Path,
    remote_server: str,
    remote_path: str,
    paths_to_sync: list[str],
    rsync_options: RsyncOptions | None = None,
) -> int:
    """Publish the collected paths to the remote server using rsync --files-from."""
    if not paths_to_sync:
        log.warning("No files or directories found to publish.")
        return 0

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as tmp_file:
        tmp_file_path = Path(tmp_file.name)
        for p in paths_to_sync:
            tmp_file.write(f"{p}\n")

    try:
        remote_dest = f"{remote_server}:{remote_path}"
        base_opts = rsync_options or RsyncOptions()
        opts = replace(base_opts, files_from=tmp_file_path)

        log.info("Publishing %d item(s) to %s...", len(paths_to_sync), remote_dest)
        manager = get_live_manager()
        stage_ctx = (
            manager.stage("Publish deliverables", 1) if manager else nullcontext()
        )
        with (
            stage_ctx as stage,
            stage.item(remote_dest) if stage else nullcontext() as item,
        ):
            result = await rsync(
                target_base_dir, remote_dest, content_only=True, options=opts
            )
            if result.returncode == 0:
                log.info("Successfully published documentation to %s", remote_dest)
                return 0
            if item:
                item.fail()
            log.error(
                "Publish failed with returncode %d: %s",
                result.returncode,
                result.stderr,
            )
            return result.returncode
    finally:
        if tmp_file_path.exists():
            tmp_file_path.unlink()
