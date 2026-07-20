"""Top-level orchestration for the metadata processing task."""

import asyncio
from collections.abc import Sequence
import logging
from pathlib import Path
import time

from rich.console import Console

from ...cli.cmd_portal.process import parse_portal_config
from ...cli.context import DocBuildContext
from ...constants import DEFAULT_DELIVERABLES
from ...models.deliverable import Deliverable
from ...models.doctype import Doctype
from ..repository import shared_worktrees, update_managed_repositories
from .discovery import iter_doctype_groups
from .manifest import compile_manifest, write_manifest_json
from .progress import report_failed_deliverables, run_metadata_progress

stdout = Console()
log = logging.getLogger(__name__)


def _collect_repo_urls(deliverables: Sequence[Deliverable]) -> set[str]:
    """Return repository URLs referenced by the deliverables."""
    return {
        str(repo)
        for deliverable in deliverables
        if (repo := deliverable.xml.git_remote()) is not None
    }


def _collect_repo_branches(
    deliverables: Sequence[Deliverable],
) -> set[tuple[str, str]]:
    """Return repository and branch pairs needed for a deliverable group."""
    repo_branches: set[tuple[str, str]] = set()
    for deliverable in deliverables:
        if not deliverable.git:
            continue
        repo_url = deliverable.git.url
        repo_branches.add((repo_url, deliverable.branch))
        for info in deliverable.translations.values():
            branch = info.branch if info.branch is not None else deliverable.branch
            repo_branches.add((repo_url, branch))
    return repo_branches


async def process_doctype_group(
    context: DocBuildContext,
    product: str,
    docset: str,
    deliverables: Sequence[Deliverable],
    *,
    repo_dir: Path,
    updated_repos: set[str],
    meta_cache_dir: Path,
    json_cache_dir: Path,
    limit: int,
    skip_repo_update: bool,
) -> None:
    """Process one product and docset group for metadata extraction.

    :param context: The DocBuild context with environment configuration.
    :param product: Product identifier for display purposes.
    :param docset: Docset identifier for display purposes.
    :param deliverables: Deliverables in the product and docset group.
    :param repo_dir: Root directory for bare repositories.
    :param updated_repos: Set of repo URLs already updated in this run.
    :param meta_cache_dir: Base directory for metadata cache output.
    :param json_cache_dir: Base directory for manifest JSON output.
    :param limit: Maximum number of concurrent operations.
    :param skip_repo_update: Skip repository update step when True.
    """
    if skip_repo_update:
        log.info("Skipping repository updates for %s/%s", product, docset)
    else:
        await update_managed_repositories(
            repo_dir,
            _collect_repo_urls(deliverables),
            updated_repos,
            limit=limit,
        )

    env = context.envconfig
    assert env is not None
    tmp_repo_dir = Path(env.paths.tmp_repo_dir).expanduser()

    async with shared_worktrees(
        repo_dir,
        tmp_repo_dir,
        _collect_repo_branches(deliverables),
        limit=limit,
    ) as worktrees:
        description = f"{product}/{docset} ({len(deliverables)})"
        status_map = await run_metadata_progress(
            context,
            deliverables,
            meta_cache_dir=meta_cache_dir,
            limit=limit,
            description=description,
            worktrees=worktrees,
        )

    successful = [
        deliverable
        for deliverable in deliverables
        if status_map.get(deliverable.full_id) == "OK"
    ]

    started_at = time.perf_counter()
    manifest = await asyncio.to_thread(compile_manifest, product, docset, successful)
    log.info(
        "Compiling manifest for %s/%s took %.3fs",
        product,
        docset,
        time.perf_counter() - started_at,
    )

    if manifest is not None:
        output_path = json_cache_dir / product / f"{docset}.json"
        await asyncio.to_thread(write_manifest_json, output_path, manifest)

    report_failed_deliverables(deliverables, status_map)


async def process(
    context: DocBuildContext,
    doctypes: Sequence[Doctype] | None,
    *,
    exitfirst: bool = False,
    skip_repo_update: bool = False,
) -> int:
    """Process metadata retrieval for the selected deliverable groups.

    :param context: The DocBuildContext containing environment configuration.
    :param doctypes: Doctype selectors to process.
    :param exitfirst: If True, stop processing on the first failure.
    :param skip_repo_update: If True, skip updating Git repositories first.
    :return: Zero on completion.
    """
    del exitfirst

    env = context.envconfig
    assert env is not None
    configdir = Path(env.paths.config_dir).expanduser()
    main_portal_config = Path(env.paths.main_portal_config).expanduser()
    stdout.print(f"Config path: {configdir}")

    appconfig = context.appconfig
    limit = appconfig.max_workers if appconfig and appconfig.max_workers else 1
    log.info("Using concurrency limit: %d", limit)
    repo_dir = Path(env.paths.repo_dir).expanduser()
    updated_repos: set[str] = set()
    meta_cache_dir = Path(env.paths.meta_cache_dir).expanduser()
    json_cache_dir = Path(env.paths.json_cache_dir).expanduser()

    portalnode = await parse_portal_config(main_portal_config)

    if not doctypes:
        doctypes = [Doctype.from_str(DEFAULT_DELIVERABLES)]

    for product, docset, deliverables in iter_doctype_groups(portalnode, doctypes):
        await process_doctype_group(
            context,
            product,
            docset,
            deliverables,
            repo_dir=repo_dir,
            updated_repos=updated_repos,
            meta_cache_dir=meta_cache_dir,
            json_cache_dir=json_cache_dir,
            limit=limit,
            skip_repo_update=skip_repo_update,
        )

    return 0
