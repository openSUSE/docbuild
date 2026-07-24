"""Progress rendering and failure reporting for metadata processing."""

import asyncio
from collections.abc import Sequence
import logging
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, TaskID, TextColumn, TimeElapsedColumn
from rich.text import Text

from ...cli.context import DocBuildContext
from ...models.deliverable import Deliverable
from ...utils.concurrency import TaskFailedError, run_parallel
from .collect import collect_dynamic_metadata

stdout = Console()
log = logging.getLogger(__name__)


def marker_for_status(status: str, spinner_char: str) -> tuple[str, str]:
    """Return marker character and style for a status."""
    if status == "OK":
        return ".", "green"
    if status == "FAILED":
        return "F", "red"
    return spinner_char, "yellow"


def build_markers(
    deliverables: Sequence[Deliverable],
    status_map: dict[str, str],
    spinner_char: str,
) -> Text:
    """Build the status marker line for the progress display."""
    markers = Text("  ")
    for index, deliverable in enumerate(deliverables):
        status = status_map.get(deliverable.full_id, "FAILED")
        marker, style = marker_for_status(status, spinner_char)
        if index:
            markers.append(" ")
        markers.append(marker, style=style)
    return markers


def finalize_status_map(status_map: dict[str, str]) -> None:
    """Normalize any pending status to failed."""
    for deliverable_id, status in status_map.items():
        if status == "PENDING":
            status_map[deliverable_id] = "FAILED"


def report_failed_deliverables(
    deliverables: Sequence[Deliverable],
    status_map: dict[str, str],
) -> None:
    """Print a summary of failed deliverables."""
    failed_deliverables = [
        deliverable
        for deliverable in deliverables
        if status_map.get(deliverable.full_id) == "FAILED"
    ]
    if not failed_deliverables:
        return

    stdout.print("Failed deliverables:")
    for deliverable in failed_deliverables:
        lang = str(deliverable.xml.lang)
        dcfile = deliverable.xml.dcfile or deliverable.xml.id
        identifier = (
            f"{deliverable.xml.productid}/{deliverable.xml.docsetid}/"
            f"{lang}:{dcfile}"
        )
        stdout.print(f"  - {identifier}")


async def run_metadata_progress(
    context: DocBuildContext,
    deliverables: Sequence[Deliverable],
    *,
    meta_cache_dir: Path,
    limit: int,
    description: str,
    worktrees: dict[tuple[str, str], Path],
) -> dict[str, str]:
    """Run metadata collection with a live progress display.

    :param context: The DocBuild context with environment configuration.
    :param deliverables: Deliverables to process.
    :param meta_cache_dir: Base directory for metadata cache output.
    :param limit: Maximum number of concurrent operations.
    :param description: Progress description label.
    :param worktrees: Dictionary of shared worktrees keyed by repo URL and branch.
    :return: Status map keyed by deliverable ID.
    """
    status_map: dict[str, str] = {
        deliverable.full_id: "PENDING" for deliverable in deliverables
    }
    spinner_chars = ["|", "/", "-", "\\"]
    spinner_index = 0

    def update_progress(progress: Progress, task_id: TaskID) -> None:
        nonlocal spinner_index
        spinner_index += 1
        completed = sum(status != "PENDING" for status in status_map.values())
        success_count = sum(status == "OK" for status in status_map.values())
        failed_count = sum(status == "FAILED" for status in status_map.values())
        spinner_char = spinner_chars[spinner_index % len(spinner_chars)]
        summary = Text(f"{success_count}/{failed_count}/{len(deliverables)}")
        progress.update(
            task_id,
            completed=completed,
            markers=build_markers(deliverables, status_map, spinner_char),
            summary=summary,
        )

    async def collect(deliverable: Deliverable) -> tuple[bool, Deliverable]:
        return await collect_dynamic_metadata(
            context,
            deliverable,
            meta_cache_dir=meta_cache_dir,
            worktrees=worktrees,
        )

    stop_event = asyncio.Event()

    async def refresh_loop(progress: Progress, task_id: TaskID) -> None:
        while not stop_event.is_set():
            update_progress(progress, task_id)
            await asyncio.sleep(0.2)

    with Progress(
        TextColumn("{task.description}"),
        TextColumn("{task.fields[markers]}"),
        TimeElapsedColumn(),
        TextColumn("{task.fields[summary]}"),
        console=stdout,
        transient=False,
    ) as progress:
        task_id: TaskID = progress.add_task(
            description,
            total=len(deliverables),
            markers=build_markers(deliverables, status_map, spinner_chars[0]),
            summary=Text(f"0/0/{len(deliverables)}"),
        )
        refresher = asyncio.create_task(refresh_loop(progress, task_id))
        async for result in run_parallel(deliverables, collect, limit=limit):
            if isinstance(result, TaskFailedError):
                log.error(
                    "Metadata task failed for %s: %s",
                    result.item.full_id,
                    result.original_exception,
                )
                status_map[result.item.full_id] = "FAILED"
                update_progress(progress, task_id)
                continue

            success, deliverable = result
            if success:
                status_map[deliverable.full_id] = "OK"
            else:
                status_map[deliverable.full_id] = "FAILED"
                log.error("Metadata generation failed for %s", deliverable.full_id)
            update_progress(progress, task_id)

        finalize_status_map(status_map)
        update_progress(progress, task_id)
        stop_event.set()
        await asyncio.gather(refresher)

    return status_map
