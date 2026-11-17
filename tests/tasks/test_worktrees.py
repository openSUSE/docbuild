"""Unit tests for worktree orchestration."""

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

from docbuild.models.deliverable import Deliverable
from docbuild.models.run import BuildRunState, DeliverableStatus
from docbuild.tasks.worktrees import _safe_process_one, process_with_shared_worktrees


@pytest.mark.asyncio
async def test_process_shared_worktrees_skips_missing_git(tmp_path: Path) -> None:
    """Ensure deliverables missing Git configurations do not crash the pipeline."""
    # Create a deliverable with NO git attribute
    mock_d = Mock(spec=Deliverable, full_id="missing:git")
    mock_d.git = None  # Explicitly missing
    mock_d.format = {}

    async def dummy_process(d: Deliverable, wt: Path) -> tuple[bool, Deliverable]:
        return True, d

    failed = await process_with_shared_worktrees(
        [mock_d],
        tmp_path,
        tmp_path,
        max_workers=2,
        semaphore=asyncio.Semaphore(2),
        process_single_func=dummy_process,
    )

    # It should gracefully fail and return the deliverable in the failed list, not crash!
    assert len(failed) == 1
    assert failed[0].full_id == "missing:git"


@pytest.mark.asyncio
async def test_process_shared_worktrees_records_missing_git_in_run_state(
    tmp_path: Path,
) -> None:
    """Ensure missing git records FAILED status against each enabled format."""
    mock_d = Mock(spec=Deliverable, full_id="missing:git")
    mock_d.git = None
    mock_d.xml = Mock(
        product_id="sles",
        docset_path="15",
        lang="en-us",
        dcfile="DC",
        productname="SLES",
    )
    mock_d.format = {"html": True, "pdf": True, "single-html": False}
    mock_d.branch = "main"

    run_state = BuildRunState(
        run_id=1,
        run_id_str="build-1",
        role="test",
        environment="test",
        start_time=datetime.now(UTC),
    )
    run_state.record_deliverable(
        product="sles",
        docset="15",
        lang="en-us",
        format="html",
        status=DeliverableStatus.UNSTARTED,
    )
    run_state.record_deliverable(
        product="sles",
        docset="15",
        lang="en-us",
        format="pdf",
        status=DeliverableStatus.UNSTARTED,
    )

    async def dummy_process(d: Deliverable, wt: Path) -> tuple[bool, Deliverable]:
        return True, d

    failed = await process_with_shared_worktrees(
        [mock_d],
        tmp_path,
        tmp_path,
        max_workers=2,
        semaphore=asyncio.Semaphore(2),
        process_single_func=dummy_process,
        run_state=run_state,
    )

    assert len(failed) == 1
    assert len(run_state.deliverables) == 2
    for r in run_state.deliverables:
        assert r.status == DeliverableStatus.FAILED
        assert r.stage == "git config"
        assert r.format in ("html", "pdf")


@pytest.mark.asyncio
async def test_safe_process_one_records_exception_in_run_state(tmp_path: Path) -> None:
    """Ensure exceptions caught by _safe_process_one update pre-registered format rows to FAILED."""
    mock_d = Mock(spec=Deliverable, full_id="sles:15:html")
    mock_d.git = Mock(url="https://github.com/SUSE/doc.git")
    mock_d.xml = Mock(
        product_id="sles",
        docset_path="15",
        lang="en-us",
        dcfile="DC",
        productname="SLES",
    )
    mock_d.format = {"html": True}
    mock_d.branch = "main"

    run_state = BuildRunState(
        run_id=2,
        run_id_str="build-2",
        role="test",
        environment="test",
        start_time=datetime.now(UTC),
    )
    run_state.record_deliverable(
        product="sles",
        docset="15",
        lang="en-us",
        format="html",
        status=DeliverableStatus.UNSTARTED,
    )

    async def failing_process(d: Deliverable, wt: Path) -> tuple[bool, Deliverable]:
        raise ValueError("Build crashed unexpectedly")

    semaphore = asyncio.Semaphore(1)
    success, _ = await _safe_process_one(
        mock_d, tmp_path, semaphore, failing_process, run_state=run_state
    )

    assert not success
    assert run_state.deliverables[0].status == DeliverableStatus.FAILED
    assert run_state.deliverables[0].stage == "build execution"
    assert "Build crashed unexpectedly" in (run_state.deliverables[0].error or "")
