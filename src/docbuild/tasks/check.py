"""Logic for checking DC file availability in remote repositories."""

from collections.abc import Sequence
import logging
from pathlib import Path

from lxml import etree

from docbuild.constants import DEFAULT_DELIVERABLES, DEFAULT_LANGS
from docbuild.models.deliverable import Deliverable
from docbuild.models.doctype import Doctype
from docbuild.models.language import LanguageCode
from docbuild.models.repo import Repo
from docbuild.tasks.metadata.deliverables import get_deliverable_from_doctype
from docbuild.tasks.metadata.prebuilt import find_html_path
from docbuild.tasks.portal import parse_portal_config
from docbuild.utils.git import ManagedGitRepo

log = logging.getLogger(__name__)

type Expectation = tuple[str, str, str, str, bool]
"""``(identifier, dcfile, repo_surl, dcpath, translation)``"""

type Planned = tuple[str, str, Expectation]
"""``(repo_url, branch, expectation)``"""


def resolve_source(deliverable: Deliverable) -> Deliverable:
    """Return the deliverable that defines the repository and DC file.

    A reference (``<xref>``) points to a deliverable that may live in another
    repository, so the target deliverable is used instead.
    """
    if (
        deliverable.xml.is_xref
        and deliverable.xml.target_type == "deliverable"
        and deliverable.xml.final_target_node is not deliverable.xml.node
    ):
        return Deliverable(deliverable.xml.final_target_node)
    return deliverable


def is_linked(deliverable: Deliverable) -> bool:
    """Return ``True`` if the deliverable is a reference to a product or docset."""
    return deliverable.xml.is_xref and deliverable.xml.target_type in ("product", "docset")


def make_identifier(deliverable: Deliverable) -> str:
    """Return the ``product/docset/lang`` identifier of a deliverable."""
    return f"{deliverable.xml.product_id}/{deliverable.xml.docset_path}/{deliverable.xml.lang}"


def resolve_repo(deliverable: Deliverable) -> tuple[Deliverable, Repo] | None:
    """Return the defining deliverable and its repository, or ``None`` without one."""
    source = resolve_source(deliverable)
    repo = source.git
    if not isinstance(repo, Repo):
        return None
    return source, repo


def prebuilt_status(
    deliverable: Deliverable,
    prebuilt_dir: Path | None,
) -> tuple[str, str] | None:
    """Return ``(href, status)`` for a prebuilt deliverable, or ``None``.

    The status is ``found`` if the prebuilt HTML exists below ``prebuilt_dir``,
    otherwise ``missing``. Prebuilt deliverables without an HTML ``<url>``
    (for example, PDF-only ones) are skipped.
    """
    href = deliverable.xml.resolved_prebuilt_html_url
    if href is None:
        return None
    if prebuilt_dir is not None and find_html_path(prebuilt_dir, deliverable, href):
        return href, "found"
    return href, "missing"


def make_dcpath(subdir: str, dcfile: str) -> str:
    """Return the path of a DC file inside a repository."""
    return "/".join(part for part in (subdir, dcfile) if part)


def make_expectation(deliverable: Deliverable) -> Planned | None:
    """Return the plan for a deliverable in its own language, or ``None``."""
    if not deliverable.xml.dcfile:
        log.debug("Skipping deliverable without DC file: %s", deliverable.xml)
        return None

    if (resolved := resolve_repo(deliverable)) is None:
        log.warning("No usable repository for deliverable: %s", deliverable.xml)
        return None
    source, repo = resolved

    dcfile = source.xml.dcfile
    expectation = (
        make_identifier(deliverable),
        dcfile,
        repo.surl,
        make_dcpath(source.subdir, dcfile),
        False,
    )
    return repo.url, source.branch, expectation


def translation_expectation(english: Deliverable, lang: str) -> Planned | None:
    """Return the plan for an English deliverable in translation ``lang``.

    The translation is checked on the branch and subdir of its ``<locale>``,
    which is looked up in the docset of the English deliverable.
    """
    locale = english.xml.locale(lang)
    if locale is None:
        log.debug("No %s locale for deliverable: %s", lang, english.xml)
        return None

    resolved = resolve_repo(english)
    if resolved is None:
        return None
    source, repo = resolved
    dcfile = source.xml.dcfile
    if not dcfile:
        return None

    try:
        branch = english.xml.branch(lang) or english.branch
    except ValueError:
        log.warning("No branch found for %s translation of: %s", lang, english.xml)
        return None
    subdir = english.xml.subdir(lang)
    expectation = (
        f"{english.xml.product_id}/{english.xml.docset_path}/{lang}",
        dcfile,
        repo.surl,
        make_dcpath(subdir, dcfile),
        True,
    )
    return repo.url, branch, expectation


def plan_deliverables(
    stitch_tree: etree._ElementTree,
    doctype: Doctype,
) -> list[tuple[Deliverable, Planned | None]]:
    """Return the deliverables of a doctype paired with their plans.

    Translations are derived from the English deliverables, so a translation
    without its own deliverables is still checked.
    """
    planned = []
    for lang in doctype.langs:
        if lang.language == DEFAULT_LANGS[0]:
            scope = doctype.model_copy(update={"langs": [lang]})
            for d in get_deliverable_from_doctype(stitch_tree, scope):
                made = None if is_linked(d) else make_expectation(d)
                planned.append((d, made))
        else:
            scope = doctype.model_copy(
                update={"langs": [LanguageCode(language=DEFAULT_LANGS[0])]}
            )
            for d in get_deliverable_from_doctype(stitch_tree, scope):
                if (made := translation_expectation(d, lang.language)) is not None:
                    planned.append((d, made))
    return planned


async def verify_repository_files(
    repo_url: str,
    branch: str,
    expectations: list[Expectation],
    repo_root: Path,
) -> dict[Expectation, str]:
    """Clone a repository and return the status of each expectation.

    The status is ``found``, ``skipped`` or ``missing``.
    """
    available: set[str] | None = None
    repo_handler = ManagedGitRepo(repo_url, repo_root)

    if await repo_handler.clone_bare():
        if await repo_handler.has_branch(branch):
            available = set(await repo_handler.ls_tree(branch))
        else:
            log.debug("Branch %r not found in %s", branch, repo_url)
            available = set()
    else:
        log.debug("Repository inaccessible: %s", repo_url)

    statuses = {}
    for expectation in expectations:
        *_, dcpath, translation = expectation
        if available is not None and dcpath in available:
            statuses[expectation] = "found"
        elif translation:
            statuses[expectation] = "skipped"
        else:
            statuses[expectation] = "missing"
    return statuses


def plan_doctypes(
    stitch_tree: etree._ElementTree,
    doctypes: Sequence[Doctype],
) -> list[tuple[Deliverable, Expectation | None]]:
    """Expand wildcards in the doctypes and plan all their deliverables."""
    planned = []
    for dt in doctypes:
        for concrete in dt.iter_doctypes(stitch_tree.getroot()):
            planned.extend(plan_deliverables(stitch_tree, concrete))
    return planned


async def verify_groups(
    groups: dict[tuple[str, str], list[Expectation]],
    repo_root: Path,
) -> dict[Expectation, str]:
    """Verify the expectations of every ``(repo_url, branch)`` group."""
    statuses: dict[Expectation, str] = {}
    for (url, branch), expectations in groups.items():
        statuses.update(
            await verify_repository_files(url, branch, expectations, repo_root)
        )
    return statuses


async def check_repository_files(
    main_portal_config: Path,
    repo_root: Path,
    doctypes: Sequence[Doctype] | None,
    prebuilt_dir: Path | None = None,
) -> list[tuple[str, str, str, str]]:
    """Verify DC file existence and return ``(identifier, dcfile, repo_surl, status)``."""
    if not main_portal_config.exists():
        log.warning("Main portal config not found: %s", main_portal_config)
        return []

    stitch_tree = await parse_portal_config(main_portal_config)

    if not doctypes:
        doctypes = [Doctype.from_str(DEFAULT_DELIVERABLES)]

    planned = plan_doctypes(stitch_tree, doctypes)

    if not planned:
        log.warning("No deliverables found for the selected doctypes.")
        return []

    groups: dict[tuple[str, str], list[Expectation]] = {}
    for _, made in planned:
        if made is not None:
            url, branch, expectation = made
            groups.setdefault((url, branch), []).append(expectation)

    statuses = await verify_groups(groups, repo_root)

    results: list[tuple[str, str, str, str]] = []
    for d, made in planned:
        if made is not None:
            _, _, expectation = made
            identifier, dcfile, repo_surl, _, _ = expectation
            results.append((identifier, dcfile, repo_surl, statuses[expectation]))
        elif is_linked(d):
            results.append((make_identifier(d), d.xml.target_id, "", "linked"))
        elif d.xml.is_prebuilt and (checked := prebuilt_status(d, prebuilt_dir)):
            href, status = checked
            results.append((make_identifier(d), href, "", status))
    return results
