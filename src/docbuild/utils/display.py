"""Reusable Live UI components for DocBuild."""
from collections import Counter, deque
from collections.abc import Iterator
from contextlib import contextmanager
import contextvars
from dataclasses import dataclass
from enum import StrEnum
import logging
from logging.handlers import QueueListener
from typing import Self

from rich.console import Console, Group, RenderableType
from rich.live import Live
from rich.markup import escape
from rich.panel import Panel
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

ACTIVE_LIVE_MANAGER = contextvars.ContextVar('ACTIVE_LIVE_MANAGER', default=None)

def get_live_manager() -> "LiveProgressManager | None":
    """Get the active live progress manager."""
    return ACTIVE_LIVE_MANAGER.get()



class LiveLogHandler(logging.Handler):
    """A logging handler that safely routes logs to a Rich Live display."""

    def __init__(self, display_manager: "LiveProgressManager", max_lines: int = 20) -> None:
        super().__init__()
        self.display_manager = display_manager
        self.max_lines = max_lines
        self.log_buffer: deque[Text] = deque(maxlen=max_lines)

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record to the live display."""
        try:
            msg = self.format(record)
            # Color code based on level
            color = {
                logging.DEBUG: "dim",
                logging.INFO: "white",
                logging.WARNING: "warning",
                logging.ERROR: "error",
                logging.CRITICAL: "error",
            }.get(record.levelno, "white")

            text = Text(msg, style=color)
            self.log_buffer.append(text)
            self.display_manager.update_logs(list(self.log_buffer))
        except Exception:
            self.handleError(record)



class ItemState(StrEnum):
    """Final outcome of a single item, storing its Rich markup prefix."""

    SUCCEEDED = "[succeeded]✔"
    SKIPPED = "[skipped]↷"
    FAILED = "[failed]✘"


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

        # Add the log buffer and split layout

        self.log_buffer = []
        self.max_log_lines = 10
        self.layout = Group(self._progress, Panel(Text(""), title="Live Logs", border_style="dim"))

        # Override the live display to render the Group instead of just the progress bar
        self.live = Live(self.layout, console=console, refresh_per_second=4)
        self._original_listener: QueueListener | None = None
        self._live_handler: LiveLogHandler | None = None

    @property
    def failed(self) -> bool:
        """Return True if any stage recorded a failure."""
        return any(stage.failed for stage in self.stages)

    def __enter__(self) -> Self:
        """Start the live view."""
        self._token = ACTIVE_LIVE_MANAGER.set(self)

        # Intercept docbuild logs
        from docbuild.logging import _LOGGING_STATE
        self._original_listener = _LOGGING_STATE["listener"].get()

        self._live_handler = LiveLogHandler(self, max_lines=self.max_log_lines)
        self._live_handler.setLevel(logging.INFO)
        self._muted_handlers = []

        if self._original_listener:
            # Mute terminal output but keep listener pulling logs
            for h in self._original_listener.handlers:
                if h.__class__.__name__ == "StreamHandler":
                    self._muted_handlers.append((h, h.level))
                    h.setLevel(logging.CRITICAL + 1)

            # Inject LiveLogHandler directly into the running listener
            self._original_listener.handlers = tuple([*list(self._original_listener.handlers), self._live_handler])
        else:
            logging.getLogger("docbuild").addHandler(self._live_handler)

        self.live.start()
        return self

    def __exit__(self, *exc_info: object) -> None:
        """Stop the live view."""
        self.live.stop()

        if self._original_listener:
            # Remove LiveLogHandler and unmute terminal
            self._original_listener.handlers = tuple(h for h in self._original_listener.handlers if h is not self._live_handler)
            for h, lvl in self._muted_handlers:
                h.setLevel(lvl)
        elif self._live_handler:
            logging.getLogger("docbuild").removeHandler(self._live_handler)

        self._live_handler = None

        if hasattr(self, "_token"):
            ACTIVE_LIVE_MANAGER.reset(self._token)

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



    def update_logs(self) -> None:
        """Update the log panel with the latest buffered lines."""
        log_text = Text("\n").join(self.log_buffer)
        self.layout.renderables[1] = Panel(log_text, title="Live Logs", border_style="dim")
        self.live.refresh()
