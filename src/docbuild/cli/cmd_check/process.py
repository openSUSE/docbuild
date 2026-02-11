"""Logic for checking DC file availability in remote repositories."""

import logging
from typing import cast

from lxml import etree

from docbuild.cli.context import DocBuildContext
from docbuild.config.xml.stitch import create_stitchfile
from docbuild.models.config.env import EnvConfig
from docbuild.utils.git import ManagedGitRepo

log = logging.getLogger(__name__)


def _group_by_repo(deliverables: list[etree._Element]) -> dict[tuple[str, str], list[str]]:
    """Group deliverable files by their repository and branch."""
    groups: dict[tuple[str, str], list[str]] = {}
    for deli_node in deliverables:
        dc_node = deli_node.find("dc")
        dcfile = dc_node.text if dc_node is not None else None

        branch_node = deli_node.find("branch")
        branch = branch_node.text if branch_node is not None else "main"

        repo = None
        # Using local-name here as well to ensure ancestor lookup survives namespaces
        git_nodes = deli_node.xpath("ancestor::*[local-name()='docset']"
                                    "/*[local-name()='builddocs']"
                                    "/*[local-name()='git']")
        if git_nodes:
            repo = git_nodes[0].get("remote")

        if repo and dcfile:
            groups.setdefault((repo, branch), []).append(dcfile)

    return groups


async def process_check_files(ctx: DocBuildContext, doctype_filter: str | None = None) -> list[str]:
    """Verify DC file existence and return a list of missing files."""
    log.info("Starting DC file availability check...")

    env_config = cast(EnvConfig, ctx.envconfig)

    # Access paths directly; models ensure they are Path objects
    config_dir = env_config.paths.config_dir.resolve()
    repo_root = env_config.paths.repo_dir.resolve()

    # 1. Get the list of XML files from the config directory
    xml_files = list(config_dir.glob("*.xml"))
    if not xml_files:
        log.warning(f"No XML files found in {config_dir}")
        return []

    # 2. Use the official stitcher to parse and merge configuration
    stitch_tree = await create_stitchfile(xml_files)

    # 3. Extraction using local-name() to bypass namespace issues
    # This prevents the "No deliverables found" error seen by the reviewer
    deliverables = stitch_tree.xpath("//*[local-name()='deliverable']")

    if not deliverables:
        log.error("No deliverables found. Check your XML structure.")
        return []

    # 4. Optional Filtering (Feature Parity with metadata/build)
    if doctype_filter:
        log.info(f"Filtering check for doctype: {doctype_filter}")

    # 5. Grouping deliverables by repo/branch to minimize network calls
    groups = _group_by_repo(deliverables)
    log.info(f"Grouped into {len(groups)} unique repo/branch combinations.")

    # 6. Verification Loop
    missing_files: list[str] = []
    for (repo_url, branch), dc_files in groups.items():
        log.info(f"Checking Repo: {repo_url} [{branch}]")
        repo_handler = ManagedGitRepo(repo_url, repo_root)

        # Attempt to prepare the bare repository
        if not await repo_handler.clone_bare():
            log.error(f"Failed to access repository: {repo_url}")
            missing_files.extend(str(dc) for dc in dc_files)
            continue

        # Get list of files in the remote branch
        available_files = await repo_handler.ls_tree(branch)
        for dc in dc_files:
            if dc in available_files:
                log.info(f"Found: {dc}")
            else:
                log.error(f"Missing: {dc}")
                missing_files.append(str(dc))

    return missing_files
