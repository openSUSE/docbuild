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


def _safe_get(obj: object, attr_name: str, default: object | None = None) -> object | None:
    """Safely extract an attribute whether it's a property or a method."""
    if not hasattr(obj, attr_name):
        return default
    attr = getattr(obj, attr_name)
    return attr() if callable(attr) else attr


async def check_repository_files(  # noqa: C901

    main_portal_config: Path,
    repo_root: Path,
    prebuilt_dir: Path,
    doctypes: Sequence[Doctype] | None
) -> dict[str, list[FileCheckResult]]:
    """Verify DC file existence using official Deliverable models."""
    log.info("Starting DC file availability check...")

    # 1. Parse the main portal config (including XIncludes)
    if not main_portal_config.exists():
        log.error("Main portal config not found: %s", main_portal_config)
        raise FileNotFoundError(f"Main portal config not found: {main_portal_config}")

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
            view = _safe_get(d, "xml")
            if not view:
                continue

            is_xref = getattr(view, "is_xref", False)
            target_type = getattr(view, "target_type", None)

            # 1. Skip structural xrefs that point to docsets or products immediately
            if is_xref and target_type in ("product", "docset"):
                continue

            # 2. Extract properties using target_id
            dcfile = getattr(view, "dcfile", None)
            is_prebuilt = getattr(view, "is_prebuilt", False)
            target_id = getattr(view, "target_id", "Unknown")

            # 3. Skip anything that still isn't a physical file or prebuilt
            if not dcfile and not is_prebuilt:
                continue

            display_name = dcfile or target_id
            is_default_lang = _safe_get(d, "lang_is_default", True)

            # Resolve actual remote repo properties from final target
            actual_d = d
            if is_xref:
                final_node = getattr(view, "final_target_node", None)
                if final_node is not None:
                    actual_d = Deliverable(final_node)

            if is_prebuilt:
                found = False
                candidates = []
                if target_id and target_id != "Unknown":
                    candidates.extend([str(target_id), f"{target_id}.zip", f"{target_id}.tar.gz"])

                basefile = getattr(view, "basefile", None)
                if basefile:
                    candidates.append(str(basefile))
                if dcfile:
                    candidates.append(str(dcfile))

                # Verify against local disk
                for cand in candidates:
                    if cand and (prebuilt_dir / cand).exists():
                        found = True
                        break

                status = "found" if found else ("error" if is_default_lang else "skipped")
                results[dt_str].append(FileCheckResult(dt_str, str(display_name), status, True))
                continue

            git_obj = _safe_get(actual_d, "git")
            if not git_obj:
                results[dt_str].append(FileCheckResult(dt_str, str(display_name), "skipped", False))
                continue

            branch = _safe_get(actual_d, "branch") or "main"
            subdir = _safe_get(actual_d, "subdir") or ""
            url = _safe_get(git_obj, "url")

            if not url:
                results[dt_str].append(FileCheckResult(dt_str, str(display_name), "skipped", False))
                continue

            key = (str(url), str(branch))
            repo_queries.setdefault(key, []).append((str(subdir), dt_str, dcfile, str(display_name), is_default_lang))

    for (url, branch), items in repo_queries.items():
        repo_handler = ManagedGitRepo(url, repo_root)

        if not await repo_handler.clone_bare():
            log.error("Repository inaccessible: %s", url)
            for _, dt_str, _, display_name, is_default_lang in items:
                status = "error" if is_default_lang else "skipped"
                results[dt_str].append(FileCheckResult(dt_str, str(display_name), status))
            continue

        available_files = await repo_handler.ls_tree(branch)

        for subdir, dt_str, target_dcfile, display_name, is_default_lang in items:
            if not target_dcfile:
                target_dcfile = display_name

            check_path = str(target_dcfile)
            if subdir and subdir != ".":
                check_path = f"{subdir}/{target_dcfile}"
            check_path = check_path.strip("/")

            found = (check_path in available_files) or (str(target_dcfile) in available_files)
            status = "found" if found else ("error" if is_default_lang else "skipped")

            results[dt_str].append(FileCheckResult(dt_str, str(display_name), status))

    return results
