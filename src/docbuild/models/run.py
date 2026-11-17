"""Data models for build run state and outcome tracking."""

from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
import threading
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr


class DeliverableStatus(StrEnum):
    """Execution status for a single deliverable."""

    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    UNSTARTED = "unstarted"


class RunOutcome(StrEnum):
    """Overall outcome of an entire build run."""

    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DeliverableResult(BaseModel):
    """Structured result of building an individual deliverable."""

    model_config = ConfigDict(extra="forbid")

    product: str = Field(..., description="Product acronym or identifier.")
    docset: str = Field(..., description="Docset or version identifier.")
    lang: str = Field(..., description="Language code (e.g. en-us).")
    format: str | None = Field(
        default=None, description="Output format (e.g. html, pdf, epub)."
    )
    status: DeliverableStatus = Field(
        default=DeliverableStatus.UNSTARTED, description="Execution outcome."
    )
    dcfile: str | None = Field(default=None, description="DC filename.")
    title: str | None = Field(default=None, description="Document title if known.")
    stage: str | None = Field(
        default=None, description="Pipeline stage where failure occurred, if any."
    )
    error: str | None = Field(
        default=None, description="Error message or stderr snippet."
    )
    log_file: str | None = Field(
        default=None, description="Path to diagnostic log file if published."
    )
    repo_url: str | None = Field(default=None, description="Git repository URL.")
    branch: str | None = Field(default=None, description="Git branch.")
    commit: str | None = Field(default=None, description="Git commit hash.")
    start_time: datetime | None = Field(
        default=None, description="Timestamp when building this deliverable began."
    )
    end_time: datetime | None = Field(
        default=None, description="Timestamp when building this deliverable completed."
    )
    duration_seconds: float | None = Field(
        default=None, description="Duration in seconds."
    )


class BuildRunState(BaseModel):
    """Structured data model capturing metadata and deliverable results for a build run."""

    model_config = ConfigDict(extra="forbid")

    run_id: int = Field(..., description="Monotonic sequential build run ID.")
    run_id_str: str = Field(
        ..., description="Formatted string representation of run ID (e.g. build-123)."
    )
    role: str = Field(
        ..., description="Environment role (e.g. production, staging, development)."
    )
    environment: str = Field(..., description="Descriptive environment name.")
    start_time: datetime = Field(
        ..., description="Timestamp when the build run started."
    )
    end_time: datetime | None = Field(
        default=None, description="Timestamp when the build run completed."
    )
    duration_seconds: float | None = Field(
        default=None, description="Total duration in seconds."
    )
    overall_outcome: RunOutcome = Field(
        default=RunOutcome.SUCCESS, description="Overall outcome of the build run."
    )
    run_dir: Path | None = Field(
        default=None, description="Filesystem directory allocated for this build run."
    )
    deliverables: list[DeliverableResult] = Field(
        default_factory=list, description="Per-deliverable results."
    )

    _lock: threading.Lock = PrivateAttr(default_factory=threading.Lock)

    @property
    def total_count(self) -> int:
        """Return the total number of deliverables tracked."""
        with self._lock:
            return len(self.deliverables)

    @property
    def success_count(self) -> int:
        """Return the number of successfully built deliverables."""
        with self._lock:
            return sum(
                1 for d in self.deliverables if d.status == DeliverableStatus.SUCCESS
            )

    @property
    def failed_count(self) -> int:
        """Return the number of failed deliverables."""
        with self._lock:
            return sum(
                1 for d in self.deliverables if d.status == DeliverableStatus.FAILED
            )

    @property
    def skipped_count(self) -> int:
        """Return the number of skipped deliverables."""
        with self._lock:
            return sum(
                1 for d in self.deliverables if d.status == DeliverableStatus.SKIPPED
            )

    @property
    def unstarted_count(self) -> int:
        """Return the number of unstarted deliverables."""
        with self._lock:
            return sum(
                1 for d in self.deliverables if d.status == DeliverableStatus.UNSTARTED
            )

    def record_deliverable(
        self,
        *,
        product: str,
        docset: str,
        lang: str,
        format: str | None = None,  # noqa: A002
        status: DeliverableStatus = DeliverableStatus.UNSTARTED,
        dcfile: str | None = None,
        title: str | None = None,
        stage: str | None = None,
        error: str | None = None,
        log_file: str | None = None,
        repo_url: str | None = None,
        branch: str | None = None,
        commit: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        duration_seconds: float | None = None,
    ) -> DeliverableResult:
        """Thread-safely record or update a deliverable result in the run state."""
        if duration_seconds is None and start_time and end_time:
            duration_seconds = round((end_time - start_time).total_seconds(), 2)

        result = DeliverableResult(
            product=product,
            docset=docset,
            lang=lang,
            format=format,
            status=status,
            dcfile=dcfile,
            title=title,
            stage=stage,
            error=error,
            log_file=log_file,
            repo_url=repo_url,
            branch=branch,
            commit=commit,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration_seconds,
        )

        with self._lock:
            # Check if this deliverable/format already exists (e.g. updating an unstarted placeholder)
            for idx, existing in enumerate(self.deliverables):
                if (
                    existing.product == product
                    and existing.docset == docset
                    and existing.lang == lang
                    and existing.format == format
                    and (
                        existing.dcfile == dcfile
                        or existing.dcfile is None
                        or dcfile is None
                    )
                ):
                    if result.dcfile is None and existing.dcfile is not None:
                        result.dcfile = existing.dcfile
                    if result.title is None and existing.title is not None:
                        result.title = existing.title
                    if result.repo_url is None and existing.repo_url is not None:
                        result.repo_url = existing.repo_url
                    if result.branch is None and existing.branch is not None:
                        result.branch = existing.branch
                    self.deliverables[idx] = result
                    return result

            self.deliverables.append(result)
            return result

    def finish(self, outcome: RunOutcome | None = None) -> None:
        """Finalize the build run state, recording end timestamp and overall outcome."""
        with self._lock:
            if outcome is not None:
                self.overall_outcome = outcome
            elif any(d.status == DeliverableStatus.FAILED for d in self.deliverables):
                self.overall_outcome = RunOutcome.FAILED
            else:
                self.overall_outcome = RunOutcome.SUCCESS

            if self.end_time is None:
                self.end_time = datetime.now(UTC)
            if self.duration_seconds is None and self.start_time:
                self.duration_seconds = round(
                    (self.end_time - self.start_time).total_seconds(), 2
                )

    def to_json(self, indent: int = 2) -> str:
        """Serialize state model to JSON formatted string."""
        with self._lock:
            return self.model_dump_json(indent=indent)

    def save(self, destination: Path | None = None) -> Path:
        """Persist the build run state to a JSON file."""
        target_path = destination or (
            self.run_dir / "run_state.json" if self.run_dir else Path("run_state.json")
        )
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(self.to_json(), encoding="utf-8")
        return target_path

    @classmethod
    def load(cls, source: Path) -> Self:
        """Deserialize a build run state from a JSON file."""
        return cls.model_validate_json(source.read_text(encoding="utf-8"))
