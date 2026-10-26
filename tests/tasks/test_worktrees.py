"""Unit tests for worktree orchestration."""

import asyncio
from pathlib import Path
from unittest.mock import Mock

import pytest

from docbuild.models.deliverable import Deliverable
from docbuild.tasks.worktrees import process_with_shared_worktrees


@pytest.mark.asyncio
async def test_process_shared_worktrees_skips_missing_git(tmp_path: Path) -> None:
    """Ensure deliverables missing Git configurations do not crash the pipeline."""
    # Create a deliverable with NO git attribute
    mock_d = Mock(spec=Deliverable, full_id="missing:git")
    mock_d.git = None  # Explicitly missing

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
