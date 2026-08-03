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
) -> tuple[bool, Deliverable]:
    """Process a single deliverable asynchronously.

    Creates a temporary clone of the deliverable's repository, checks out the
    correct branch, and executes DAPS to generate metadata.

    :param deliverable: The Deliverable object to process.
    :param repo_dir: Path to the base repositories directory.
    :param tmp_repo_dir: Path to the temporary worktree directory.
    :param meta_cache_dir: Path to the metadata cache output directory.
    :param dapstmpl: A template string with the daps command and potential placeholders.
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
        async with PersistentOnErrorTemporaryDirectory(
            dir=str(tmp_repo_dir),
            prefix=(
                f"clone-{deliverable.xml.productid}-{deliverable.xml.docsetid}"
                f"-{deliverable.xml.lang}-{deliverable.xml.dcfile}_"
            ),
        ) as worktree_dir:
            mg = ManagedGitRepo(deliverable.git.url, repo_dir)
            if not await mg.clone_bare():
                raise RuntimeError(
                    f"Failed to ensure bare repository for {deliverable.full_id}"
                )

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

        update_metadata_json(outputjson, deliverable)
        log.debug("Updated metadata JSON for %s", deliverable.full_id)
        return True, deliverable

    except Exception as e:
        log.error("Error processing %s: %s", deliverable.full_id, str(e))
        return False, deliverable
