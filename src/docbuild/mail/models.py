"""Data models and failure collection for email notifications."""

from collections import defaultdict
from dataclasses import dataclass, field
import threading


@dataclass(frozen=True, slots=True)
class FailureRecord:
    """Record of a deliverable build failure for notification reporting."""

    product_id: str
    docset: str = ""
    lang: str = ""
    format: str | None = None
    stage: str = "build"
    error: str = ""
    maintainers: tuple[str, ...] = field(default_factory=tuple)
    repo_url: str | None = None
    branch: str | None = None
    commit: str | None = None
    dcfile: str | None = None
    title: str | None = None
    log_path: str | None = None


class FailureCollector:
    """Thread-safe collector for tracking failures during build runs."""

    def __init__(self) -> None:
        """Initialize an empty failure collector."""
        self._failures: list[FailureRecord] = []
        self._lock = threading.Lock()

    def add(self, failure: FailureRecord) -> None:
        """Add a failure record thread-safely."""
        with self._lock:
            self._failures.append(failure)

    @property
    def failures(self) -> list[FailureRecord]:
        """Return a snapshot copy of all recorded failures."""
        with self._lock:
            return list(self._failures)

    def by_product(self) -> dict[str, list[FailureRecord]]:
        """Group failures by product_id for product-maintainer notifications."""
        grouped: dict[str, list[FailureRecord]] = defaultdict(list)
        for failure in self.failures:
            if failure.product_id:
                grouped[failure.product_id].append(failure)
        return dict(grouped)

    def unattributed(self) -> list[FailureRecord]:
        """Return failures that cannot be attributed to a specific product."""
        return [f for f in self.failures if not f.product_id]
