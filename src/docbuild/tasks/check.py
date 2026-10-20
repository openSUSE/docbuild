"""Logic for checking DC file availability in remote repositories."""

from collections.abc import Sequence
from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Literal

from docbuild.constants import DEFAULT_DELIVERABLES
from docbuild.models.deliverable import Deliverable
from docbuild.models.doctype import Doctype
from docbuild.tasks.metadata.deliverables import get_deliverable_from_doctype
from docbuild.tasks.portal import parse_portal_config
from docbuild.utils.git import ManagedGitRepo

log = logging.getLogger(__name__)


@dataclass
class FileCheckResult:
    """Result of checking a single DC file in the remote repository."""

    doctype: str
    dcfile: str
    status: Literal["found", "skipped", "error"]
    is_prebuilt: bool = False


async def check_repository_files(  # noqa: C901

    main_portal_config: Path,
    repo_root: Path,
    doctypes: Sequence[Doctype] | None
) -> dict[str, list[FileCheckResult]]:
    """Verify DC file existence using official Deliverable models."""
    log.info("Starting DC file availability check...")

    # 1. Parse the main portal config (including XIncludes)
    if not main_portal_config.exists():
        log.warning("Main portal config not found: %s", main_portal_config)
        return {}

    stitch_tree = await parse_portal_config(main_portal_config)

    # 2. Identify target doctypes (use defaults if none provided)
    if not doctypes:
        doctypes = [Doctype.from_str(DEFAULT_DELIVERABLES)]

    results: dict[str, list[FileCheckResult]] = {}
    repo_queries = {}

    for dt in doctypes:
        dt_str = str(dt)
        results[dt_str] = []

        deliverables = list(get_deliverable_from_doctype(stitch_tree, dt))
        if not deliverables:
            # Handle empty locale naturally without throwing a blocking error
            log.debug("No deliverables found for doctype %s. (Possibly empty locale)", dt_str)
            continue

        for d in deliverables:
            # Safely extract dcfile (handling both properties and methods)
            dcfile_val = getattr(d.xml, "dcfile", None)
            dcfile = dcfile_val() if callable(dcfile_val) else dcfile_val
            if not dcfile:
                dcfile = "None"

            # Check for xref and resolve to the ultimate target
            is_xref_val = getattr(d.xml, "is_xref", None)
            is_xref = is_xref_val() if callable(is_xref_val) else is_xref_val

            actual_d = d
            if is_xref:
                final_node_val = getattr(d.xml, "final_target_node", None)
                final_node = final_node_val() if callable(final_node_val) else final_node_val
                if final_node is not None:
                    actual_d = Deliverable(final_node)

            is_prebuilt_val = getattr(actual_d.xml, "is_prebuilt", None)
            is_prebuilt = is_prebuilt_val() if callable(is_prebuilt_val) else is_prebuilt_val

            git_val = getattr(actual_d, "git", None)
            git_obj = git_val() if callable(git_val) else git_val

            if is_prebuilt or git_obj is None:
                results[dt_str].append(FileCheckResult(
                    doctype=dt_str,
                    dcfile=dcfile,
                    status="skipped",
                    is_prebuilt=True
                ))
                continue

            branch_val = getattr(actual_d, "branch", None)
            branch = branch_val() if callable(branch_val) else branch_val
            branch = branch or "main"

            is_default_val = getattr(d, "lang_is_default", None)
            is_default_lang = is_default_val() if callable(is_default_val) else is_default_val

            key = (git_obj.url, branch)
            repo_queries.setdefault(key, []).append((actual_d, dt_str, dcfile, is_default_lang))

    for (url, branch), items in repo_queries.items():
        repo_handler = ManagedGitRepo(url, repo_root)

        if not await repo_handler.clone_bare():
            log.error("Repository inaccessible: %s", url)
            for _actual_d, dt_str, dcfile, is_default_lang in items:
                status = "error" if is_default_lang else "skipped"
                results[dt_str].append(FileCheckResult(dt_str, dcfile, status))
            continue

        available_files = await repo_handler.ls_tree(branch)

        for actual_d, dt_str, dcfile, is_default_lang in items:
            subdir_val = getattr(actual_d, "subdir", None)
            subdir = subdir_val() if callable(subdir_val) else subdir_val

            target_file = dcfile
            if subdir and subdir != ".":
                target_file = f"{subdir}/{dcfile}"

            target_file = target_file.strip("/")

            # Accommodate full subtree paths and generic names
            found = (target_file in available_files) or (dcfile in available_files)

            if found:
                status = "found"
            else:
                status = "error" if is_default_lang else "skipped"

            results[dt_str].append(FileCheckResult(dt_str, dcfile, status))

    return results
