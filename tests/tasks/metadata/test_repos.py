"""Unit tests for docbuild.tasks.metadata.repos."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from docbuild.models.deliverable import Deliverable
from docbuild.models.repo import Repo
import docbuild.tasks.metadata.repos as repos_pkg
from docbuild.tasks.metadata.repos import update_repositories


@pytest.mark.asyncio
class TestUpdateRepositories:
    """Tests for the update_repositories function."""

    @patch.object(repos_pkg.ManagedGitRepo, "clone_bare", new_callable=AsyncMock)
    async def test_success(self, mock_clone_bare: AsyncMock, tmp_path: Path):
        """Verify update_repositories returns True when all repos clone successfully."""
        mock_deliverable = Mock(spec=Deliverable)
        mock_repo = Mock(spec=Repo)
        mock_repo.configure_mock(url="gh://SUSE/doc-test", name="SUSE/doc-test")
        mock_deliverable.git = mock_repo
        mock_clone_bare.return_value = True

        result = await update_repositories([mock_deliverable], tmp_path / "repos")

        assert result is True
        mock_clone_bare.assert_awaited_once()

    @patch.object(repos_pkg.ManagedGitRepo, "clone_bare", new_callable=AsyncMock)
    async def test_failure_logged(
        self, mock_clone_bare: AsyncMock, tmp_path: Path, caplog
    ):
        """Verify update_repositories logs an error and returns False on failure."""
        mock_deliverable = Mock(spec=Deliverable)
        mock_repo = Mock(spec=Repo)
        mock_repo.configure_mock(
            url="gh://SUSE/non-existent-repo", name="SUSE/non-existent-repo"
        )
        mock_deliverable.git = mock_repo
        mock_clone_bare.return_value = False

        result = await update_repositories([mock_deliverable], tmp_path / "repos")

        mock_clone_bare.assert_awaited_once()
        assert result is False
        assert "Failed to update" in caplog.text


@pytest.mark.asyncio
async def test_concurrent_repo_items(tmp_path, monkeypatch):
    """Shared repositories get one live item and one outcome per URL."""
    from docbuild.utils.display import ItemState, LiveProgressManager

    docs = []
    for name in ("first", "second", "first"):
        doc = Mock(spec=Deliverable)
        doc.git = Repo(f"https://github.com/SUSE/{name}.git")
        docs.append(doc)

    both_running = asyncio.Event()
    with LiveProgressManager(disable=True) as manager, manager.stage("repos") as stage:

        async def clone(repo):
            if len(stage.running) == 2:
                both_running.set()
            await asyncio.wait_for(both_running.wait(), timeout=2)
            return repo.remote_url == docs[0].git.url

        monkeypatch.setattr(repos_pkg.ManagedGitRepo, "clone_bare", clone)
        assert not await update_repositories(docs, tmp_path)

    assert stage.counts == {ItemState.SUCCEEDED: 1, ItemState.FAILED: 1}
    assert not stage.running


@pytest.mark.asyncio
@pytest.mark.parametrize("error", [OSError, TypeError, asyncio.CancelledError])
async def test_clone_exception(tmp_path, monkeypatch, error):
    doc = Mock(spec=Deliverable)
    doc.git = Repo("https://github.com/SUSE/doc-test.git")
    monkeypatch.setattr(
        repos_pkg.ManagedGitRepo, "clone_bare", AsyncMock(side_effect=error)
    )
    if error is OSError:
        assert not await update_repositories([doc], tmp_path)
    else:
        with pytest.raises(error):
            await update_repositories([doc], tmp_path)
