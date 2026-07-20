"""Tests for repository synchronization helpers."""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

import docbuild.tasks.repository.sync as repo_sync_mod
from docbuild.tasks.repository.sync import update_managed_repositories
from docbuild.utils.concurrency import TaskFailedError


def _logged_message_contains(mock_log: Mock, text: str) -> bool:
    """Return True when a mocked logger received a matching format string."""
    return any(
        text in " ".join(str(arg) for arg in call.args)
        for call in mock_log.call_args_list
        if call.args
    )


@pytest.mark.asyncio
class TestUpdateManagedRepositories:
    """Tests for update_managed_repositories."""

    @patch.object(repo_sync_mod, "ManagedGitRepo")
    async def test_update_managed_repositories_success(
        self,
        mock_repo_class: Mock,
        tmp_path: Path,
    ) -> None:
        """Verify repositories are updated successfully."""
        mock_repo = AsyncMock()
        mock_repo.clone_bare.return_value = True
        mock_repo.slug = "SUSE-doc-test"
        mock_repo_class.return_value = mock_repo

        updated_repos: set[str] = set()
        updated = await update_managed_repositories(
            tmp_path / "repos",
            {"gh://SUSE/doc-test"},
            updated_repos,
            limit=1,
        )

        assert updated == ["SUSE-doc-test"]
        assert "gh://SUSE/doc-test" in updated_repos
        mock_repo.clone_bare.assert_awaited_once()

    @patch.object(repo_sync_mod, "ManagedGitRepo")
    async def test_update_managed_repositories_failed(
        self,
        mock_repo_class: Mock,
        tmp_path: Path,
    ) -> None:
        """Verify failures are reported when repo updates fail."""
        mock_repo = AsyncMock()
        mock_repo.clone_bare.return_value = False
        mock_repo.slug = "SUSE-fail"
        mock_repo_class.return_value = mock_repo

        updated_repos: set[str] = set()
        with patch.object(repo_sync_mod.log, "error") as mock_error:
            updated = await update_managed_repositories(
                tmp_path / "repos",
                {"gh://SUSE/fail"},
                updated_repos,
                limit=1,
            )

        assert updated == []
        assert _logged_message_contains(mock_error, "Failed to update repository")

    @patch.object(repo_sync_mod, "ManagedGitRepo")
    async def test_update_managed_repositories_skips_known_urls(
        self,
        mock_repo_class: Mock,
        tmp_path: Path,
    ) -> None:
        """Do not recreate managed repositories that were already updated."""
        updated = await update_managed_repositories(
            tmp_path / "repos",
            {"gh://SUSE/doc-test"},
            {"gh://SUSE/doc-test"},
            limit=1,
        )

        assert updated == []
        mock_repo_class.assert_not_called()

    @patch.object(repo_sync_mod, "ManagedGitRepo")
    async def test_update_managed_repositories_logs_task_failure(
        self,
        mock_repo_class: Mock,
        tmp_path: Path,
    ) -> None:
        """Log task wrapper failures emitted by the concurrency helper."""
        repo = Mock()
        repo.slug = "SUSE-doc-test"
        mock_repo_class.return_value = repo

        async def fake_run_parallel(items, worker_fn, limit):
            del items, worker_fn, limit
            yield TaskFailedError(repo, RuntimeError("boom"))

        with (
            patch.object(repo_sync_mod, "run_parallel", new=fake_run_parallel),
            patch.object(repo_sync_mod.log, "error") as mock_error,
        ):
            updated = await update_managed_repositories(
                tmp_path / "repos",
                {"gh://SUSE/doc-test"},
                set(),
                limit=1,
            )

        assert updated == []
        assert _logged_message_contains(
            mock_error,
            "Failed to update repository",
        )
