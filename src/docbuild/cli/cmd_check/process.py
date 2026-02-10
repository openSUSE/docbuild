"""Logic for checking DC file availability in remote repositories."""

import logging
from pathlib import Path
from typing import cast

from lxml import etree

from docbuild.cli.context import DocBuildContext
from docbuild.models.config.env import EnvConfig
from docbuild.utils.git import ManagedGitRepo

log = logging.getLogger(__name__)


def _extract_deliverables(config_dir: Path) -> list[etree._Element]:
    """Find and parse all deliverable nodes from XML files."""
    all_deliverables = []
    xml_files = list(config_dir.glob("*.xml"))

    for xml_file in xml_files:
        try:
            tree = etree.parse(str(xml_file))
            found = tree.xpath("//deliverable")
            log.info(f"File {xml_file.name}: Found {len(found)} deliverable(s)")
            all_deliverables.extend(found)
        except Exception as e:
            log.error(f"Failed to parse {xml_file.name}: {e}")
    return all_deliverables


def _group_by_repo(deliverables: list[etree._Element]) -> dict[tuple[str, str], list[str]]:
    """Group deliverable files by their repository and branch."""
    groups: dict[tuple[str, str], list[str]] = {}
    for deli_node in deliverables:
        try:
            dc_node = deli_node.find("dc")
            dcfile = dc_node.text if dc_node is not None else None

            branch_node = deli_node.find("branch")
            branch = branch_node.text if branch_node is not None else "main"

            repo = None
            git_nodes = deli_node.xpath("ancestor::docset/builddocs/git")
            if git_nodes:
                repo = git_nodes[0].get("remote")

            if repo and dcfile:
                groups.setdefault((repo, branch), []).append(dcfile)
        except Exception as e:
            log.debug(f"Error extracting data from node: {e}")
    return groups


async def process_check_files(ctx: DocBuildContext) -> bool:
    """Verify DC file existence in Git repos using optimized grouping."""
    log.info("Starting DC file availability check...")

    env_config = cast(EnvConfig, ctx.envconfig)
    config_dir = Path(env_config.paths.config_dir).resolve()
    repo_root = Path(env_config.paths.repo_dir).resolve()

    # 1. Extraction
    deliverables = _extract_deliverables(config_dir)
    if not deliverables:
        log.error("No deliverables found. Check your XML structure.")
        return False

    # 2. Grouping
    groups = _group_by_repo(deliverables)
    log.info(f"Grouped into {len(groups)} unique repo/branch combinations.")

    # 3. Verification Loop
    missing_count = 0
    for (repo_url, branch), dc_files in groups.items():
        log.info(f"Checking Repo: {repo_url} [{branch}]")
        repo_handler = ManagedGitRepo(repo_url, repo_root)

        if not await repo_handler.clone_bare():
            missing_count += len(dc_files)
            continue

        available_files = await repo_handler.ls_tree(branch)
        for dc in dc_files:
            if dc in available_files:
                log.info(f"Found: {dc}")
            else:
                log.error(f"Missing: {dc}")
                missing_count += 1

    return missing_count == 0
