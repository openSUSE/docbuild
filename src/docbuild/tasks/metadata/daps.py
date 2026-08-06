"""DAPS command construction and deliverable processing."""

import asyncio
import logging
from pathlib import Path
import shlex

from docbuild.models.deliverable import Deliverable
from docbuild.utils.contextmgr import PersistentOnErrorTemporaryDirectory, edit_json
from docbuild.utils.git import ManagedGitRepo

log = logging.getLogger(__name__)


def get_daps_command(
    worktree_dir: Path,
    dcfile_path: Path,
    outputjson: Path,
    dapstmpl: str,
) -> list[str]:
    """Construct the DAPS command for native execution.

    :param worktree_dir: The working directory for the git worktree.
    :param dcfile_path: Absolute path to the DC file within the worktree.
    :param outputjson: Path where DAPS should write its JSON output.
    :param dapstmpl: A template string with ``{builddir}``, ``{dcfile}``,
        and ``{output}`` placeholders.
    :return: A list of command arguments suitable for ``subprocess.exec``.
    """
    raw_daps_cmd = dapstmpl.format(
        builddir=str(worktree_dir),
        dcfile=str(dcfile_path),
        output=str(outputjson),
    )
    return shlex.split(raw_daps_cmd)


def update_metadata_json(outputjson: Path, deliverable: Deliverable) -> None:
    """Update the generated metadata JSON with deliverable-specific details.

    :param outputjson: Path to the JSON file written by DAPS.
    :param deliverable: The Deliverable whose metadata should be merged in.
    """
    fmt = deliverable.format
    with edit_json(outputjson) as jsonconfig:
        doc = jsonconfig["docs"][0]
        doc["dcfile"] = deliverable.xml.dcfile
        doc["format"]["html"] = deliverable.paths.html_path
        if fmt.get("pdf"):
            doc["format"]["pdf"] = deliverable.paths.pdf_path
        if fmt.get("single-html"):
            doc["format"]["single-html"] = deliverable.paths.singlehtml_path
        doc["lang"] = str(deliverable.xml.lang)
        # Keep category at the document level, not per translated doc entry.
        doc.pop("category", None)
        if category := deliverable.xml.categoryid:
            jsonconfig["category"] = category


async def process_deliverable(
    deliverable: Deliverable,
    repo_dir: Path,
    tmp_repo_dir: Path,
    meta_cache_dir: Path,
    *,
    dapstmpl: str,
    skip_repo_update: bool = False,
) -> tuple[bool, Deliverable]:
    """Process a single deliverable asynchronously.

    Creates a temporary clone of the deliverable's repository, checks out the
    correct branch, and executes DAPS to generate metadata.

    :param deliverable: The Deliverable object to process.
    :param repo_dir: Path to the base repositories directory.
    :param tmp_repo_dir: Path to the temporary worktree directory.
    :param meta_cache_dir: Path to the metadata cache output directory.
    :param dapstmpl: A template string with the daps command and potential placeholders.
    :param skip_repo_update: If True, do not update/fetch the bare repository.
    :return: A tuple of ``(success, deliverable)``.
    """
    log.info("> Processing deliverable: %s", deliverable.full_id)

    if not deliverable.xml.dcfile:
        log.debug("Deliverable %s has no DC file (prebuilt), skipping.", deliverable.full_id)
        return True, deliverable

    bare_repo_path = repo_dir / deliverable.git.slug
    if not bare_repo_path.is_dir():
        log.error(
            "Bare repository not found for %s at %s",
            deliverable.git.name,
            bare_repo_path,
        )
        return False, deliverable

    outputdir = meta_cache_dir / deliverable.paths.relpath
    outputdir.mkdir(parents=True, exist_ok=True)
    outputjson = outputdir / deliverable.xml.dcfile

    try:
        mg = ManagedGitRepo(deliverable.git.url, repo_dir)
        if not skip_repo_update:
            if not await mg.clone_bare():
                raise RuntimeError(
                    f"Failed to ensure bare repository for {deliverable.full_id}"
                )

        async with PersistentOnErrorTemporaryDirectory(
            dir=str(tmp_repo_dir),
            prefix=(
                f"wt-{deliverable.xml.productid}-{deliverable.xml.docsetid}"
                f"-{deliverable.xml.lang}-{deliverable.xml.dcfile}_"
            ),
        ) as worktree_dir:
            try:
                await mg.create_worktree(worktree_dir, deliverable.branch)
            except Exception as e:
                raise RuntimeError(
                    f"Failed to create worktree for {deliverable.full_id}: {e}"
                ) from e

            full_dcfile_path = (
                Path(worktree_dir) / deliverable.subdir / deliverable.xml.dcfile
            )

            cmd = get_daps_command(
                Path(worktree_dir),
                full_dcfile_path,
                outputjson,
                dapstmpl,
            )

            daps_proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr_data = await daps_proc.communicate()

            if daps_proc.returncode != 0:
                log.error("DAPS Error: %s", stderr_data.decode())
                raise RuntimeError(f"DAPS failed for {deliverable.full_id}")

        await mg.prune_worktrees()
        update_metadata_json(outputjson, deliverable)
        log.debug("Updated metadata JSON for %s", deliverable.full_id)
        return True, deliverable

    except Exception as e:
        log.error("Error processing %s: %s", deliverable.full_id, str(e))
        return False, deliverable


async def _run_daps_for_deliverable(
    deliverable: Deliverable,
    worktree_dir: Path,
    meta_cache_dir: Path,
    dapstmpl: str,
) -> tuple[bool, Deliverable]:
    """Run daps for one deliverable inside an existing worktree.

    :param deliverable: The Deliverable to process.
    :param worktree_dir: Path to an already-checked-out working tree.
    :param meta_cache_dir: Path to the metadata cache output directory.
    :param dapstmpl: Template string for the DAPS metadata command.
    :return: A tuple of ``(success, deliverable)``.
    """
    log.info("> Processing deliverable: %s", deliverable.full_id)

    if not deliverable.xml.dcfile:
        log.debug("Deliverable %s has no DC file (prebuilt), skipping.", deliverable.full_id)
        return True, deliverable

    outputdir = meta_cache_dir / deliverable.paths.relpath
    outputdir.mkdir(parents=True, exist_ok=True)
    outputjson = outputdir / deliverable.xml.dcfile

    full_dcfile_path = worktree_dir / deliverable.subdir / deliverable.xml.dcfile
    cmd = get_daps_command(worktree_dir, full_dcfile_path, outputjson, dapstmpl)

    try:
        daps_proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr_data = await daps_proc.communicate()

        if daps_proc.returncode != 0:
            log.error("DAPS Error for %s: %s", deliverable.full_id, stderr_data.decode())
            return False, deliverable

        update_metadata_json(outputjson, deliverable)
        log.debug("Updated metadata JSON for %s", deliverable.full_id)
        return True, deliverable

    except Exception as e:
        log.error("Error processing %s: %s", deliverable.full_id, str(e))
        return False, deliverable


async def process_deliverable_group(
    deliverables: list[Deliverable],
    repo_dir: Path,
    tmp_repo_dir: Path,
    meta_cache_dir: Path,
    dapstmpl: str,
    semaphore: asyncio.Semaphore,
    *,
    skip_repo_update: bool = False,
) -> list[Deliverable]:
    """Process all deliverables that share the same repository and branch.

    Creates a single worktree for the group and runs daps for each deliverable
    concurrently within it, subject to the shared semaphore.

    :param deliverables: Deliverables sharing the same ``(git.url, branch)`` pair.
    :param repo_dir: Path to the base repositories directory.
    :param tmp_repo_dir: Path to the temporary worktree directory.
    :param meta_cache_dir: Path to the metadata cache output directory.
    :param dapstmpl: Template string for the DAPS metadata command.
    :param semaphore: Shared semaphore bounding total concurrent daps processes.
    :param skip_repo_update: If True, do not update/fetch the bare repository.
    :return: A list of Deliverables that failed.
    """
    first = deliverables[0]
    mg = ManagedGitRepo(first.git.url, repo_dir)

    bare_repo_path = repo_dir / first.git.slug
    if not bare_repo_path.is_dir():
        log.error("Bare repository not found for %s at %s", first.git.name, bare_repo_path)
        return list(deliverables)

    if not skip_repo_update:
        if not await mg.clone_bare():
            log.error("Failed to ensure bare repository for %s", first.git.name)
            return list(deliverables)

    prefix = (
        f"wt-{first.xml.productid}-{first.xml.docsetid}"
        f"-{first.branch.replace('/', '-')}_"
    )
    log.info(
        "Processing group %s/%s: %d deliverable(s).",
        first.git.name, first.branch, len(deliverables),
    )
    failed: list[Deliverable] = []
    async with PersistentOnErrorTemporaryDirectory(dir=str(tmp_repo_dir), prefix=prefix) as worktree_dir:
        try:
            await mg.create_worktree(worktree_dir, first.branch)
        except Exception as e:
            log.error("Failed to create worktree for %s/%s: %s", first.git.name, first.branch, e)
            return list(deliverables)

        async def _limited(d: Deliverable) -> tuple[bool, Deliverable]:
            async with semaphore:
                return await _run_daps_for_deliverable(d, worktree_dir, meta_cache_dir, dapstmpl)

        tasks = [
            asyncio.create_task(_limited(d), name=f"daps_{d.full_id}")
            for d in deliverables
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for d, result in zip(deliverables, results, strict=False):
            if isinstance(result, Exception):
                log.error("Task error for %s: %s", d.full_id, result)
                failed.append(d)
            elif not result[0]:
                failed.append(result[1])

    await mg.prune_worktrees()
    return failed
