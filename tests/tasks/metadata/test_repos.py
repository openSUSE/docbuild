"""Unit tests for docbuild.tasks.metadata.repos."""

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
        mock_deliverable.git = Mock(spec=Repo, url="gh://SUSE/doc-test")
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
        mock_deliverable.git = Mock(spec=Repo, url="gh://SUSE/non-existent-repo")
        mock_clone_bare.return_value = False

        result = await update_repositories([mock_deliverable], tmp_path / "repos")

        mock_clone_bare.assert_awaited_once()
        assert result is False
        assert "Failed to update" in caplog.text
