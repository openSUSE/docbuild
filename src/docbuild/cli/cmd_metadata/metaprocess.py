"""Defines the handling of metadata extraction from deliverables."""

from collections.abc import Iterator, Sequence
import logging
from pathlib import Path

from lxml import etree
from rich.console import Console

from ...constants import DEFAULT_DELIVERABLES
from ...models.deliverable import Deliverable
from ...models.doctype import Doctype
from ...utils.concurrency import TaskFailedError, run_parallel
from ...utils.git import ManagedGitRepo
from ..cmd_portal.process import parse_portal_config
from ..context import DocBuildContext

# Set up rich consoles for output
stdout = Console()
console_err = Console(stderr=True, style="red")

# Set up logging
log = logging.getLogger(__name__)


def get_deliverables_for_doctype(
    root: etree._ElementTree,
    doctype: Doctype,
) -> Iterator[Deliverable]:
    """Return DC deliverables that match a single doctype.

    :param root: Parsed portal XML tree with stitched configuration.
    :param doctype: Doctype selector provided by the user.
    :return: Iterator of DC deliverables matching the selector.
    """
    # Use the doctype XPath to locate locale nodes, then filter DC deliverables.
    languages = root.getroot().xpath(doctype.xpath())
    for language in languages:
        for node in language.findall("deliverable"):
            deliverable = Deliverable(node)
            if deliverable.xml.is_dc:
                yield deliverable


def iter_doctype_groups(
    root: etree._ElementTree,
    doctypes: Sequence[Doctype],
) -> Iterator[tuple[str, str, list[Deliverable]]]:
    """Yield product/docset groups for each doctype.

    :param root: Parsed portal XML tree with stitched configuration.
    :param doctypes: Doctype selectors provided by the user.
    :yield: Tuples of (product, docset, deliverables).
    """
    for doctype in doctypes:
        deliverables = get_deliverables_for_doctype(root, doctype)
        grouped: dict[tuple[str, str], list[Deliverable]] = {}
        for deliverable in deliverables:
            product = deliverable.xml.productid
            docset = deliverable.xml.docsetid
            grouped.setdefault((product, docset), []).append(deliverable)

        for (product, docset), grouped_deliverables in grouped.items():
            yield product, docset, grouped_deliverables


async def update_repositories_for_deliverables(
    repo_dir: Path,
    repos: set[str],
    updated_repos: set[str],
    *,
    limit: int,
) -> list[str]:
    """Update bare repositories for deliverables, once per repo URL.

    :param repo_dir: Root directory for bare repositories.
    :param repos: Repository URLs derived from deliverables.
    :param updated_repos: Set of repo URLs already updated in this run.
    :param limit: Maximum number of concurrent repo updates.
    :return: List of repository slugs successfully updated in this call.
    """
    repos_to_update: list[ManagedGitRepo] = []
    for repo_url in repos:
        if repo_url in updated_repos:
            continue
        updated_repos.add(repo_url)
        repos_to_update.append(ManagedGitRepo(repo_url, repo_dir))

    if not repos_to_update:
        return []

    async def clone(repo: ManagedGitRepo) -> tuple[ManagedGitRepo, bool]:
        return repo, await repo.clone_bare()

    updated_slugs: list[str] = []
    async for result in run_parallel(repos_to_update, clone, limit=limit):
        if isinstance(result, TaskFailedError):
            log.error(
                "Failed to update repository %s: %s",
                result.item.slug,
                result.original_exception,
            )
            continue

        repo, success = result
        if not success:
            log.error("Failed to update repository %s", repo.slug)
            continue

        updated_slugs.append(repo.slug)

    return updated_slugs


async def process(
    context: DocBuildContext,
    doctypes: Sequence[Doctype] | None,
    *,
    exitfirst: bool = False,
    skip_repo_update: bool = False,
) -> int:
    """Asynchronous function to process metadata retrieval.

    :param context: The DocBuildContext containing environment configuration.
    :param doctypes: A sequence of Doctype objects to process.
    :param exitfirst: If True, stop processing on the first failure.
    :param skip_repo_update: If True, skip updating Git repositories before processing.
    :raises ValueError: If no envconfig is found or if paths are not
        configured correctly.
    :return: 0 if all files passed validation, 1 if any failures occurred.
    """
    env = context.envconfig
    configdir = Path(env.paths.config_dir).expanduser()
    main_portal_config = Path(env.paths.main_portal_config).expanduser()
    stdout.print(f"Config path: {configdir}")

    limit = context.appconfig.max_workers
    repo_dir = Path(env.paths.repo_dir).expanduser()
    updated_repos: set[str] = set()

    portalnode: etree._ElementTree = await parse_portal_config(main_portal_config)

    if not doctypes:
        doctypes = [Doctype.from_str(DEFAULT_DELIVERABLES)]

    for product, docset, deliverables in iter_doctype_groups(portalnode, doctypes):
        updated_slugs: list[str] = []
        if skip_repo_update:
            log.info("Skipping repository updates for %s/%s", product, docset)
        else:
            repos = {
                repo.url
                for deliverable in deliverables
                if (repo := deliverable.xml.git_remote()) is not None
            }
            updated_slugs = await update_repositories_for_deliverables(
                repo_dir,
                repos,
                updated_repos,
                limit=limit,
            )
        stdout.print(f"{product}/{docset}")
        for slug in sorted(updated_slugs):
            stdout.print(f"  Updated repo: {slug}")
        for deliverable in deliverables:
            stdout.print(f"  - {deliverable.full_id} type=\"dc\"")

    return 0
