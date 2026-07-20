"""Tests for metadata progress helpers."""

import asyncio
from pathlib import Path
from types import SimpleNamespace
from typing import ClassVar
from unittest.mock import AsyncMock, Mock, patch

import pytest

from docbuild.cli.context import DocBuildContext
import docbuild.tasks.metadata.progress as progress_mod
from docbuild.utils.concurrency import TaskFailedError


class DummyProgress:
    """Minimal progress object used to exercise progress updates in tests."""

    instances: ClassVar[list["DummyProgress"]] = []

    def __init__(self, *args, **kwargs) -> None:
        del args, kwargs
        self.tasks: list[tuple[str, int, object, object]] = []
        self.updates: list[dict[str, object]] = []
        type(self).instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        del exc_type, exc, tb

    def add_task(self, description, total, markers, summary):
        self.tasks.append((description, total, markers, summary))
        return 1

    def update(self, task_id, **kwargs) -> None:
        self.updates.append({"task_id": task_id, **kwargs})


class TestProgressHelpers:
    """Tests for metadata progress rendering helpers."""

    @pytest.mark.parametrize(
        ("status", "spinner_char", "expected"),
        [
            ("OK", "|", (".", "green")),
            ("FAILED", "|", ("F", "red")),
            ("PENDING", "/", ("/", "yellow")),
        ],
        ids=["ok", "failed", "pending"],
    )
    def test_marker_for_status(
        self,
        status: str,
        spinner_char: str,
        expected: tuple[str, str],
    ) -> None:
        """Return the expected marker and style for each status."""
        assert progress_mod.marker_for_status(status, spinner_char) == expected

    def test_finalize_status_map_and_report_failures(self, deliverable) -> None:
        """Normalize pending statuses and print only failed deliverables."""
        status_map = {deliverable.full_id: "PENDING"}
        progress_mod.finalize_status_map(status_map)
        assert status_map[deliverable.full_id] == "FAILED"

        with patch.object(progress_mod.stdout, "print") as mock_print:
            progress_mod.report_failed_deliverables([deliverable], status_map)
            progress_mod.report_failed_deliverables(
                [deliverable],
                {deliverable.full_id: "OK"},
            )

        assert mock_print.call_count == 2

    @pytest.mark.asyncio
    async def test_run_metadata_progress_tracks_success_and_failures(self) -> None:
        """Aggregate worker results into a final status map."""
        DummyProgress.instances.clear()
        deliverables = [
            SimpleNamespace(full_id="ok"),
            SimpleNamespace(full_id="fail"),
            SimpleNamespace(full_id="error"),
        ]
        original_sleep = asyncio.sleep

        async def fast_sleep(delay: float) -> None:
            del delay
            await original_sleep(0)

        async def fake_run_parallel(items, worker_fn, limit):
            del items, worker_fn, limit
            yield (True, deliverables[0])
            yield (False, deliverables[1])
            yield TaskFailedError(deliverables[2], RuntimeError("boom"))

        with (
            patch.object(progress_mod, "Progress", DummyProgress),
            patch.object(progress_mod, "run_parallel", new=fake_run_parallel),
            patch.object(progress_mod.asyncio, "sleep", new=fast_sleep),
        ):
            status_map = await progress_mod.run_metadata_progress(
                Mock(spec=DocBuildContext),
                deliverables,
                meta_cache_dir=Path("/tmp/meta"),
                limit=2,
                description="sles/15-sp7",
                worktrees={},
            )

        assert status_map == {"ok": "OK", "fail": "FAILED", "error": "FAILED"}
        assert DummyProgress.instances[0].tasks
        assert DummyProgress.instances[0].updates

    @pytest.mark.asyncio
    async def test_run_metadata_progress_invokes_collect_worker(
        self,
        tmp_path: Path,
    ) -> None:
        """Execute the inner collect worker through the progress pipeline."""
        DummyProgress.instances.clear()
        deliverable = SimpleNamespace(full_id="ok")
        original_sleep = asyncio.sleep

        async def fast_sleep(delay: float) -> None:
            del delay
            await original_sleep(0)

        async def inline_run_parallel(items, worker_fn, limit):
            del limit
            for item in items:
                yield await worker_fn(item)

        with (
            patch.object(progress_mod, "Progress", DummyProgress),
            patch.object(progress_mod, "run_parallel", new=inline_run_parallel),
            patch.object(progress_mod.asyncio, "sleep", new=fast_sleep),
            patch.object(
                progress_mod,
                "collect_dynamic_metadata",
                new=AsyncMock(return_value=(True, deliverable)),
            ) as mock_collect,
        ):
            status_map = await progress_mod.run_metadata_progress(
                Mock(spec=DocBuildContext),
                [deliverable],
                meta_cache_dir=tmp_path,
                limit=1,
                description="single",
                worktrees={("repo", "main"): tmp_path},
            )

        assert status_map == {"ok": "OK"}
        mock_collect.assert_awaited_once()
