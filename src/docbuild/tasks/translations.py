"""Task module for resolving available deliverable translations."""
import asyncio
from pathlib import Path

from lxml import etree

from docbuild.models.deliverable import Deliverable
from docbuild.models.doctype import Doctype
from docbuild.models.language import LanguageCode
from docbuild.tasks.metadata.runner import get_deliverable_from_doctype
from docbuild.utils.git import ManagedGitRepo


async def resolve_actual_translations(  # noqa: C901
    root: etree._ElementTree,
    doctype: Doctype,
    repo_dir: Path
) -> dict[str, set[str]]:
    """Resolve actual available translations by checking the git tree cache."""
    base_dt = doctype.model_copy(update={"langs": [LanguageCode(language="*")]})
    all_dels = await asyncio.to_thread(lambda: list(get_deliverable_from_doctype(root, base_dt)))

    tree_cache: dict[tuple[str, str], list[str]] = {}
    valid_translations: dict[str, set[str]] = {}

    for d in all_dels:
        if not (d.xml.is_dc or d.xml.is_xref):
            continue

        lang = str(d.xml.lang)
        dcfile = d.xml.dcfile
        target_id = d.xml.target_id

        eff_dcfile = dcfile
        actual_d = d

        if d.xml.is_xref:
            final_node = d.xml.final_target_node
            if final_node is not None:
                actual_d = Deliverable(final_node)
                dc_node = final_node.find("dc")
                if dc_node is not None:
                    eff_dcfile = dc_node.attrib.get("file")

        if not eff_dcfile:
            eff_dcfile = target_id
        if not eff_dcfile:
            continue

        if not (git_obj := actual_d.git):
            continue

        repo_url = git_obj.url
        branch = actual_d.branch
        subdir = actual_d.subdir

        if not repo_url:
            continue

        cache_key = (str(repo_url), str(branch))
        if cache_key not in tree_cache:
            repo = ManagedGitRepo(str(repo_url), repo_dir)
            await repo.clone_bare()
            tree_cache[cache_key] = await repo.ls_tree(str(branch))

        available_files = tree_cache[cache_key]

        check_path = str(eff_dcfile)
        if subdir and subdir != ".":
            check_path = f"{subdir}/{eff_dcfile}".strip("/")

        found = (check_path in available_files) or (str(eff_dcfile) in available_files)

        if found:
            key = target_id or eff_dcfile
            valid_translations.setdefault(str(key), set()).add(lang)

    return valid_translations
