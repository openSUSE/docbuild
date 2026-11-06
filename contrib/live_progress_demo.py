"""Demo of a LiveProgressManager with sequential stages and per-item outcomes.

Run with: uv run --frozen python contrib/live_progress_demo.py
"""

import asyncio
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import StrEnum
import logging
import random
from typing import Self

from rich.console import Console, RenderableType
from rich.logging import RichHandler
from rich.markup import escape
from rich.progress import (
    BarColumn,
    Progress,
    ProgressColumn,
    SpinnerColumn,
    Task,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Column
from rich.text import Text

log = logging.getLogger(__name__)


class ItemState(StrEnum):
    """Final outcome of a single item, storing its Rich markup prefix."""

    SUCCEEDED = "[green]✔"
    SKIPPED = "[yellow]↷"
    FAILED = "[red]✘"


def format_status(counts: Counter[ItemState]) -> str:
    """Render outcome counts with fixed-width numbers to avoid jitter."""
    return "| ".join(f"{s} {counts[s]:>3}[/]" for s in ItemState)


class MofNColumn(ProgressColumn):
    """Show 'completed/total' with the slash at a fixed position."""

    def __init__(self, digits: int = 3) -> None:
        super().__init__()
        self.digits = digits

    def render(self, task: Task) -> Text:
        """Render right-aligned completed and left-aligned total."""
        total = "?" if task.total is None else str(int(task.total))
        return Text(
            f"{int(task.completed):>{self.digits}}/{total:<{self.digits}}",
            style="progress.download",
        )


class StageProgress(Progress):
    """Progress that renders the current item on a line below each stage."""

    def get_renderables(self) -> Iterator[RenderableType]:
        """Yield each stage row followed by its running items."""
        # One table per stage, so columns need fixed widths to stay aligned.
        for task in self.tasks:
            yield self.make_tasks_table([task])
            if item := task.fields.get("item"):
                yield Text(f"  {item}", style="dim")


@dataclass(slots=True)
class Item:
    """Handle for one item; it succeeds unless skipped, failed, or raising."""

    state: ItemState | None = None

    def set_state(self, state: ItemState) -> None:
        """Set the outcome state for this item."""
        self.state = state

    def skip(self) -> None:
        """Mark the item as skipped."""
        self.state = ItemState.SKIPPED

    def fail(self) -> None:
        """Mark the item as failed without raising."""
        self.state = ItemState.FAILED


class Stage:
    """Tracks outcomes and running items of one stage in a progress task."""

    MAX_SHOWN = 3

    def __init__(
        self,
        name: str,
        progress: Progress,
        task_id: TaskID,
        total: int | None = None,
    ) -> None:
        self.name = name
        self.counts: Counter[ItemState] = Counter()
        self.running: dict[int, str] = {}
        self._progress = progress
        self._task_id = task_id
        self._total = total

    @property
    def failed(self) -> bool:
        """Return True if at least one item failed."""
        return self.counts[ItemState.FAILED] > 0

    def set_total(self, total: int | None) -> None:
        """Update the stage's total item count."""
        self._total = total
        self._progress.update(self._task_id, total=total)

    @contextmanager
    def item(self, name: str) -> Iterator[Item]:
        """Track one item; an exception marks it FAILED and propagates."""
        item = Item()
        self.running[id(item)] = name
        self.refresh()
        try:
            yield item
            if item.state is None:
                item.state = ItemState.SUCCEEDED
        except Exception:
            item.state = ItemState.FAILED
            raise
        except BaseException:
            item.state = None
            raise
        finally:
            self.running.pop(id(item), None)
            # Cancelled items have no state and are not counted.
            if item.state is not None:
                self.counts[item.state] += 1
            self.refresh(advance=int(item.state is not None))

    def refresh(self, advance: int = 0) -> None:
        """Push current counts and running items to the progress task."""
        shown = ", ".join(list(self.running.values())[: self.MAX_SHOWN])
        if (hidden := len(self.running) - self.MAX_SHOWN) > 0:
            shown += f" +{hidden}"
        self._progress.update(
            self._task_id,
            advance=advance,
            status=format_status(self.counts),
            item=shown,
        )

    def close(self, *, aborted: bool = False) -> None:
        """Finalize the stage row in the progress display."""
        done = self.counts.total()
        total = done if self._total is None or not aborted else self._total
        style = "red" if aborted or self.failed else "green"
        self._progress.update(
            self._task_id,
            total=total,
            completed=done,
            item="",
            description=f"[{style}]{escape(self.name)}",
        )
        self._progress.stop_task(self._task_id)
        task = self._progress.tasks[self._task_id]
        if task.finished_time is None:
            task.finished_time = task.elapsed


class LiveProgressManager:
    """Live view showing one progress bar per stage; stages run sequentially.

    With ``disable=True`` nothing is rendered, but outcomes are still tracked.
    """

    def __init__(
        self,
        console: Console | None = None,
        *,
        disable: bool = False,
        name_width: int = 20,
    ) -> None:
        self.stages: list[Stage] = []
        self._active: Stage | None = None
        self._progress = StageProgress(
            SpinnerColumn(finished_text="•"),
            TextColumn(
                "[bold]{task.description}",
                table_column=Column(
                    width=name_width, no_wrap=True, overflow="ellipsis"
                ),
            ),
            BarColumn(),
            MofNColumn(),
            TextColumn("{task.fields[status]}"),
            TimeElapsedColumn(),
            console=console,
            disable=disable,
        )

    @property
    def failed(self) -> bool:
        """Return True if any stage recorded a failure."""
        return any(stage.failed for stage in self.stages)

    def __enter__(self) -> Self:
        """Start the live view."""
        self._progress.start()
        return self

    def __exit__(self, *exc_info: object) -> None:
        """Stop the live view."""
        self._progress.stop()

    async def __aenter__(self) -> Self:
        """Start the live view from an async context."""
        return self.__enter__()

    async def __aexit__(self, *exc_info: object) -> None:
        """Stop the live view from an async context."""
        self.__exit__(*exc_info)

    @contextmanager
    def stage(self, name: str, total: int | None = None) -> Iterator[Stage]:
        """Open a stage; only one stage may be active at a time."""
        if self._active is not None:
            raise RuntimeError(f"Stage {self._active.name!r} is still running")
        task_id = self._progress.add_task(
            escape(name), total=total, status=format_status(Counter()), item=""
        )
        stage = self._active = Stage(name, self._progress, task_id, total=total)
        self.stages.append(stage)
        aborted = False
        try:
            yield stage
        except BaseException:  # Adjust this accordingly
            aborted = True
            raise
        finally:
            self._active = None
            stage.close(aborted=aborted)


# --- Demo -------------------------------------------------------------------

STAGES = {
    "Clone repos": [f"repo-{i:02}" for i in range(8)],
    "Build metadata": [f"sles/{v}" for v in ("15-SP6", "15-SP7", "16.0")] * 4,
    "Build deliverables": [f"doc-{i:03}" for i in range(20)],
}


async def process(name: str, stage: Stage, sem: asyncio.Semaphore) -> None:
    """Simulate work on one item with a random outcome."""
    async with sem:
        with stage.item(name) as item:
            await asyncio.sleep(random.uniform(0.1, 0.6))
            outcome = random.choices(list(ItemState), weights=(85, 10, 5))[0]
            if outcome is ItemState.SKIPPED:
                item.skip()
            elif outcome is ItemState.FAILED:
                item.fail()
                log.error("[red]Failed:[/] %s", escape(name))


async def main() -> None:
    """Run all demo stages sequentially with concurrent items."""
    console = Console()
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=[RichHandler(console=console, markup=True)],
    )
    sem = asyncio.Semaphore(4)
    async with LiveProgressManager(
        console, disable=not console.is_terminal
    ) as reporter:
        for name, items in STAGES.items():
            with reporter.stage(name, total=len(items)) as stage:
                async with asyncio.TaskGroup() as tg:
                    for item in items:
                        tg.create_task(process(item, stage, sem))


if __name__ == "__main__":
    asyncio.run(main())
