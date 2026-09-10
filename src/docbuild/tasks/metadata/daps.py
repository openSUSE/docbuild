"""DAPS command construction and deliverable processing."""

import asyncio
import json
import logging
from pathlib import Path
import shlex

from docbuild.models.cache import Cache
from docbuild.models.deliverable import Deliverable

from ...utils.contextmgr import PersistentOnErrorTemporaryDirectory, edit_json
from ...utils.git import ManagedGitRepo
from .prebuilt import extract_prebuilt_metadata

log = logging.getLogger(__name__)


async def get_daps_hashes(worktree_dir: Path, dcfile_path: Path) -> dict[str, str]:
    """Run daps list-srcfiles --hashes and parse the output.

    Converts absolute paths to relative paths based on the worktree.
    """
    cmd = ["daps", "-d", str(dcfile_path), "list-srcfiles", "--hashes"]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=worktree_dir,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout_data, stderr_data = await proc.communicate()

    if proc.returncode != 0:
        log.warning("daps list-srcfiles failed: %s", stderr_data.decode())
        return {}

    hashes = {}
    for line in stdout_data.decode().splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue

        # Output format: ABSOLUTE_PATH:MD5_HASH
        parts = line.rsplit(":", maxsplit=1)
        if len(parts) == 2:
            abs_path, md5 = parts
            try:
                # Make path relative to worktree for consistent caching across runs
                rel_path = str(Path(abs_path).relative_to(worktree_dir))
                hashes[rel_path] = md5
            except ValueError:
                hashes[abs_path] = md5

    return hashes


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


async def process_deliverable(    # noqa: C901
    deliverable: Deliverable,
    repo_dir: Path,
    tmp_repo_dir: Path,
    meta_cache_dir: Path,
    prebuilt_dir: Path,
    *,
    dapstmpl: str,
    skip_repo_update: bool = False,
    env_config_hash: str = "",
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
        log.info("Deliverable %s is prebuilt. Extracting metadata from Antora HTML...", deliverable.full_id)

        try:
            # 1. Run the extractor
            meta_dict = extract_prebuilt_metadata(deliverable, prebuilt_dir)

            # 2. Write it to the metadata cache JSON file
            outputdir = meta_cache_dir / deliverable.paths.relpath
            outputdir.mkdir(parents=True, exist_ok=True)

            # Use HTML basename for uniqueness, fallback to deliverable ID if missing
            html_url = meta_dict.get("docs", [{}])[0].get("format", {}).get("html", "")
            if html_url:
                json_filename = Path(html_url.lstrip("/")).name.replace(".html", ".json")
            else:
                json_filename = f"{deliverable._node.get('id', 'prebuilt')}.json"

            outputjson = outputdir / json_filename

            with open(outputjson, "w", encoding="utf-8") as f:
                json.dump(meta_dict, f, indent=2)

            log.debug("Successfully extracted and saved prebuilt metadata for %s", deliverable.full_id)
            return True, deliverable

        except Exception as e:
            log.error("Failed to extract metadata for prebuilt deliverable %s: %s", deliverable.full_id, e)
            return False, deliverable

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
            if not skip_repo_update:
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

            # --- CACHE CHECK LOGIC ---
            cache_file = outputdir / f"{deliverable.xml.dcfile}.cache.json"
            old_cache = Cache.from_json(cache_file)

            # Fetch current hashes using our new helper
            current_file_hashes = await get_daps_hashes(Path(worktree_dir), full_dcfile_path)
            new_cache = Cache(env_config_hash=env_config_hash, file_hashes=current_file_hashes)

            # If the hashes match and the output JSON already exists, SKIP!
            if old_cache.combined_hash == new_cache.combined_hash and cache_file.exists() and outputjson.exists():
                log.info("Cache hit for %s! Skipping DAPS execution.", deliverable.full_id)
                return True, deliverable

            log.info("Cache miss for %s. Running full build...", deliverable.full_id)

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

        # Save new cache for next time.
        new_cache.to_json(cache_file)

        log.debug("Updated metadata JSON and cache for %s", deliverable.full_id)
        return True, deliverable

    except Exception as e:
        log.error("Error processing %s: %s", deliverable.full_id, str(e))
        return False, deliverable
