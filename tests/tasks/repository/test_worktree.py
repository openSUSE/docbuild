"""Tests for shared repository worktree helpers."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

import docbuild.tasks.repository.worktree as worktree_mod


def _logged_message_contains(mock_log: Mock, text: str) -> bool:
    """Return True when a mocked logger received a matching format string."""
    return any(text in call.args[0] for call in mock_log.call_args_list if call.args)


class DummyTempDir:
    """Async context manager that returns a prepared temporary directory."""

    counter = 0

    def __init__(self, **kwargs) -> None:
        type(self).counter += 1
        self.path = Path(kwargs["dir"]) / f"{kwargs['prefix']}-{type(self).counter}"

    async def __aenter__(self) -> Path:
        self.path.mkdir(parents=True, exist_ok=True)
        return self.path

    async def __aexit__(self, exc_type, exc, tb) -> None:
        del exc_type, exc, tb


@pytest.mark.asyncio
async def test_shared_worktrees_empty_returns_empty_mapping(tmp_path: Path) -> None:
    """Yield an empty worktree mapping when no repositories are requested."""
    async with worktree_mod.shared_worktrees(
        tmp_path / "repos",
        tmp_path / "tmp",
        [],
        limit=1,
    ) as worktrees:
        assert worktrees == {}


@pytest.mark.asyncio
async def test_shared_worktrees_handles_success_and_failure(
    tmp_path: Path,
) -> None:
    """Create worktrees for successful branches and log task failures."""
    class FakeRepo:
        """Minimal managed repo used by shared worktree tests."""

        def __init__(self, url: str) -> None:
            self.remote_url = url
            self.slug = url.rsplit("/", 1)[-1]

        async def create_worktree(self, target_dir: Path, branch: str) -> None:
            target_dir.mkdir(parents=True, exist_ok=True)
            if branch == "broken":
                raise RuntimeError("broken branch")

    def fake_repo_factory(repo_url: str, repo_dir: Path):
        del repo_dir
        return FakeRepo(repo_url)

    with (
        patch.object(worktree_mod, "ManagedGitRepo", side_effect=fake_repo_factory),
        patch.object(
            worktree_mod,
            "PersistentOnErrorTemporaryDirectory",
            DummyTempDir,
        ),
        patch.object(worktree_mod.log, "error") as mock_error,
    ):
        async with worktree_mod.shared_worktrees(
            tmp_path / "repos",
            tmp_path / "tmp",
            [
                ("https://example.invalid/repo-a.git", "main"),
                ("https://example.invalid/repo-b.git", "broken"),
            ],
            limit=2,
        ) as worktrees:
            assert ("https://example.invalid/repo-a.git", "main") in worktrees
            assert ("https://example.invalid/repo-b.git", "broken") not in worktrees

    assert _logged_message_contains(mock_error, "Failed to create shared worktree")
