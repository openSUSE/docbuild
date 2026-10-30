"""Reusable Live UI components for DocBuild."""

from collections import deque
from collections.abc import Generator
from contextlib import contextmanager
import contextvars
import logging

from rich.console import Group
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.text import Text

from ..logging import _LOGGING_STATE

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
            color = "white"
            if record.levelno >= logging.ERROR:
                color = "red"
            elif record.levelno >= logging.WARNING:
                color = "yellow"
            elif record.levelno == logging.DEBUG:
                color = "dim"
            elif any(word in msg.lower() for word in ["success", "done", "finished"]):
                color = "green"

            text = Text(msg, style=color)
            self.log_buffer.append(text)
            self.display_manager.update_logs(list(self.log_buffer))
        except Exception:
            self.handleError(record)


class LiveProgressManager:
    """Manages a split-pane Rich Live UI for progress and logging."""

    def __init__(self, title: str = "Processing Tasks", log_lines: int = 15) -> None:
        self.title = title
        self.log_lines = log_lines

        # 1. Setup Progress
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            expand=True,
        )

        # 2. Setup Layout
        self.log_panel = Panel("", title="[b]Live Logs[/b]", border_style="dim", height=self.log_lines + 2)
        self.init_task = self.progress.add_task("[dim]Initializing build environment...", total=None)
        self.layout = Group(
            Panel(self.progress, title=f"[b]{self.title}[/b]", border_style="blue"),
            self.log_panel
        )

        self.live = Live(self.layout, refresh_per_second=10)
        self.log_handler = LiveLogHandler(self, max_lines=self.log_lines)

    def update_logs(self, texts: list[Text]) -> None:
        """Update the lower log panel safely."""
        self.log_panel.renderable = Group(*texts)
        # We don't strictly need to force refresh here as Live updates at 10Hz,
        # but it keeps the UI highly responsive.

    @contextmanager
    def start(self) -> Generator["LiveProgressManager", None, None]:
        """Start the live display and intercept logs."""
        # 1. Start the Rich Live UI
        token = ACTIVE_LIVE_MANAGER.set(self)
        self.live.start()

        # 2. Intercept logging
        original_handlers = []
        listener = _LOGGING_STATE["listener"].get()
        if listener:
            # We temporarily swap the handlers the QueueListener is pushing to
            original_handlers = list(listener.handlers)

            # Find the original console formatter so our UI logs look identical
            for h in original_handlers:
                if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler):
                    self.log_handler.setFormatter(h.formatter)
                    break

            # Keep FileHandlers active, but replace StreamHandlers with our UI handler
            new_handlers = [h for h in original_handlers if isinstance(h, logging.FileHandler)]
            new_handlers.append(self.log_handler)
            listener.handlers = tuple(new_handlers)

        try:
            yield self
        finally:
            # 3. Restore original logging
            if listener:
                listener.handlers = tuple(original_handlers)
            self.live.stop()
            ACTIVE_LIVE_MANAGER.reset(token)
