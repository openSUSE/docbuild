"""Logic for checking DC file availability in remote repositories."""

from collections.abc import Sequence
import logging
from pathlib import Path
from typing import cast

from docbuild.cli.cmd_metadata.metaprocess import get_deliverable_from_doctype
from docbuild.cli.context import DocBuildContext
from docbuild.config.xml.stitch import create_stitchfile
from docbuild.constants import DEFAULT_DELIVERABLES
from docbuild.models.config.env import EnvConfig
from docbuild.models.deliverable import Deliverable
from docbuild.models.doctype import Doctype
from docbuild.utils.git import ManagedGitRepo

log = logging.getLogger(__name__)


async def _verify_repository_files(
    repo_url: str,
    branch: str,
    deliverables: list[Deliverable],
    repo_root: Path,
) -> list[str]:
    """Clone a repository and check for the existence of specific DC files."""
    missing = []
    # Use the first deliverable to get the repo's abbreviated name (surl)
    repo_surl = deliverables[0].git.surl
    log.info(f"Checking Repo: {repo_surl} [{branch}]")

    repo_handler = ManagedGitRepo(repo_url, repo_root)

    if not await repo_handler.clone_bare():
        log.error(f"Repository inaccessible: {repo_surl}")
        for d in deliverables:
            # Format: [repo] product/version/lang:file
            missing.append(f"[{repo_surl}] {d.productid}/{d.docsetid}/{d.lang}:{d.dcfile}")
        return missing

    available_files = await repo_handler.ls_tree(branch)
    for d in deliverables:
        display_name = f"[{repo_surl}] {d.productid}/{d.docsetid}/{d.lang}:{d.dcfile}"
        if d.dcfile in available_files:
            log.info(f"Found: {display_name}")
        else:
            log.error(f"Missing: {display_name}")
            missing.append(display_name)
    return missing


async def process_check_files(
    ctx: DocBuildContext,
    doctypes: Sequence[Doctype] | None
) -> list[str]:
    """Verify DC file existence using official Deliverable models."""
    log.info("Starting DC file availability check...")

    env_config = cast(EnvConfig, ctx.envconfig)
    config_dir = env_config.paths.config_dir.expanduser()
    repo_root = env_config.paths.repo_dir.expanduser()

    # 1. Prepare XML and Stitch Tree
    xml_files = list(config_dir.rglob("*.xml"))
    if not xml_files:
        log.warning(f"No XML files found in {config_dir}")
        return []

    stitch_tree = await create_stitchfile(xml_files)

    # 2. Identify target doctypes (use defaults if none provided)
    if not doctypes:
        doctypes = [Doctype.from_str(DEFAULT_DELIVERABLES)]

    # 3. Use official logic to extract Deliverable objects
    all_deliverables: list[Deliverable] = []
    for dt in doctypes:
        all_deliverables.extend(get_deliverable_from_doctype(stitch_tree, dt))

    if not all_deliverables:
        log.error("No deliverables found for the selected doctypes.")
        return []

    # 4. Group by repository and branch to optimize network calls
    groups: dict[tuple[str, str], list[Deliverable]] = {}
    for d in all_deliverables:
        key = (d.git.url, d.branch or "main")
        groups.setdefault(key, []).append(d)

    # 5. Verification Loop
    missing_files: list[str] = []
    for (url, branch), deli_list in groups.items():
        results = await _verify_repository_files(url, branch, deli_list, repo_root)
        missing_files.extend(results)

    # Final success message if no files were missing
    if not missing_files:
        log.info("All DC files are available in remote repositories.")

    return missing_files
