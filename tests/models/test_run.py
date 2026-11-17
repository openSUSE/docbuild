"""Unit tests for build run state and outcome data models."""

from datetime import UTC, datetime
from pathlib import Path

from docbuild.models.run import (
    BuildRunState,
    DeliverableResult,
    DeliverableStatus,
    RunOutcome,
)


def test_deliverable_result_creation() -> None:
    """Verify DeliverableResult stores all deliverable execution facts."""
    res = DeliverableResult(
        product="sles",
        docset="15-sp5",
        lang="en-us",
        format="html",
        status=DeliverableStatus.SUCCESS,
        dcfile="DC-sles",
        title="SLES Deployment Guide",
        repo_url="https://github.com/SUSE/doc-sles.git",
        branch="main",
        commit="abc1234",
        duration_seconds=5.42,
    )
    assert res.product == "sles"
    assert res.status == DeliverableStatus.SUCCESS
    assert res.format == "html"
    assert res.duration_seconds == 5.42


def test_build_run_state_counts_and_updates() -> None:
    """Verify state model tracks deliverable counts and updates correctly."""
    now = datetime.now(UTC)
    state = BuildRunState(
        run_id=42,
        run_id_str="build-42",
        role="production",
        environment="docserv",
        start_time=now,
    )

    # Initial state
    assert state.total_count == 0
    assert state.success_count == 0
    assert state.failed_count == 0
    assert state.skipped_count == 0
    assert state.unstarted_count == 0

    # Record unstarted deliverable
    state.record_deliverable(
        product="sles",
        docset="15",
        lang="en-us",
        format="html",
        status=DeliverableStatus.UNSTARTED,
    )
    assert state.total_count == 1
    assert state.unstarted_count == 1

    # Update to success
    state.record_deliverable(
        product="sles",
        docset="15",
        lang="en-us",
        format="html",
        status=DeliverableStatus.SUCCESS,
        duration_seconds=10.0,
    )
    # Total count should still be 1 (in-place update)
    assert state.total_count == 1
    assert state.unstarted_count == 0
    assert state.success_count == 1

    # Record a failed deliverable
    state.record_deliverable(
        product="sles",
        docset="15",
        lang="en-us",
        format="pdf",
        status=DeliverableStatus.FAILED,
        stage="daps build",
        error="Syntax error in XML",
    )
    # Record a skipped deliverable
    state.record_deliverable(
        product="leap",
        docset="16.0",
        lang="en-us",
        status=DeliverableStatus.SKIPPED,
    )
    # Record another unstarted deliverable
    state.record_deliverable(
        product="sles-ha",
        docset="15",
        lang="en-us",
        format="html",
        status=DeliverableStatus.UNSTARTED,
    )

    assert state.total_count == 4
    assert state.success_count == 1
    assert state.failed_count == 1
    assert state.skipped_count == 1
    assert state.unstarted_count == 1


def test_build_run_state_finish_outcome() -> None:
    """Verify finish sets overall outcome based on deliverables."""
    now = datetime.now(UTC)
    state = BuildRunState(
        run_id=1,
        run_id_str="build-1",
        role="production",
        environment="test",
        start_time=now,
    )
    state.record_deliverable(
        product="sles",
        docset="15",
        lang="en-us",
        format="html",
        status=DeliverableStatus.SUCCESS,
    )
    state.finish()
    assert state.overall_outcome == RunOutcome.SUCCESS
    assert state.end_time is not None
    assert state.duration_seconds is not None

    # Run with a failure should finish with FAILED outcome
    state_failed = BuildRunState(
        run_id=2,
        run_id_str="build-2",
        role="production",
        environment="test",
        start_time=now,
    )
    state_failed.record_deliverable(
        product="sles",
        docset="15",
        lang="en-us",
        format="pdf",
        status=DeliverableStatus.FAILED,
    )
    state_failed.finish()
    assert state_failed.overall_outcome == RunOutcome.FAILED


def test_build_run_state_json_roundtrip(tmp_path: Path) -> None:
    """Verify JSON persistence and deserialization."""
    now = datetime.now(UTC)
    state = BuildRunState(
        run_id=10,
        run_id_str="build-10",
        role="production",
        environment="prod-server",
        start_time=now,
        run_dir=tmp_path / "10",
    )
    state.record_deliverable(
        product="sles",
        docset="15",
        lang="en-us",
        format="html",
        status=DeliverableStatus.SUCCESS,
        duration_seconds=3.14,
    )
    state.finish()

    saved_file = state.save()
    assert saved_file.is_file()

    loaded = BuildRunState.load(saved_file)
    assert loaded.run_id == 10
    assert loaded.run_id_str == "build-10"
    assert loaded.overall_outcome == RunOutcome.SUCCESS
    assert loaded.total_count == 1
    assert loaded.deliverables[0].product == "sles"
    assert loaded.deliverables[0].duration_seconds == 3.14


def test_finalize_run_state_outcomes(tmp_path: Path) -> None:
    """Verify finalize_run_state preserves CANCELLED and assigns correct outcomes."""
    from docbuild.cli.cmd_build.cmd_run import CANCELLED_EXIT_CODE, finalize_run_state

    now = datetime.now(UTC)

    # Cancelled via exit code
    state_cancel = BuildRunState(
        run_id=101,
        run_id_str="build-101",
        role="test",
        environment="test",
        start_time=now,
        run_dir=tmp_path / "101",
    )
    finalize_run_state(state_cancel, CANCELLED_EXIT_CODE)
    assert state_cancel.overall_outcome == RunOutcome.CANCELLED
    assert state_cancel.end_time is not None

    # Success (exit code 0)
    state_success = BuildRunState(
        run_id=102,
        run_id_str="build-102",
        role="test",
        environment="test",
        start_time=now,
        run_dir=tmp_path / "102",
    )
    finalize_run_state(state_success, 0)
    assert state_success.overall_outcome == RunOutcome.SUCCESS

    # Failure (nonzero exit code)
    state_fail = BuildRunState(
        run_id=103,
        run_id_str="build-103",
        role="test",
        environment="test",
        start_time=now,
        run_dir=tmp_path / "103",
    )
    finalize_run_state(state_fail, 1)
    assert state_fail.overall_outcome == RunOutcome.FAILED
