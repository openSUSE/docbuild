"""Tests for the git utility module."""

import asyncio
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import AsyncMock, patch

import pytest

from docbuild.models.repo import Repo
from docbuild.utils import git as git_module
from docbuild.utils.git import ManagedGitRepo


@pytest.fixture
def mock_subprocess_exec(monkeypatch) -> AsyncMock:
    """Fixture to mock asyncio.create_subprocess_exec."""
    process_mock = AsyncMock()
    process_mock.communicate.return_value = (b"stdout success", b"stderr info")
    process_mock.returncode = 0
    mock_create = AsyncMock(return_value=process_mock)
    monkeypatch.setattr(asyncio, "create_subprocess_exec", mock_create)
    return mock_create


@pytest.fixture
def mock_execute_git(monkeypatch) -> AsyncMock:
    """Fixture to mock execute_git_command."""
    # Remove the side_effect to allow tests to set their own return_value
    mock = AsyncMock()
    monkeypatch.setattr(git_module, "execute_git_command", mock)
    return mock


@pytest.fixture(autouse=True)
def clear_managed_repo_cache():
    """Clear the ManagedGitRepo._is_updated cache before each test."""
    ManagedGitRepo.clear_cache()


async def test_managed_repo_clone_bare_new(
    tmp_path: Path, mock_execute_git: AsyncMock, monkeypatch
):
    """Test clone_bare when the repository does not exist yet."""
    repo = ManagedGitRepo("http://a.b/org/c.git", tmp_path)
    mock_execute_git.return_value = CompletedProcess(
        args=[], returncode=0, stdout="", stderr=""
    )
    # Simulate repo does not exist
    monkeypatch.setattr(Path, "exists", lambda self: False)

    result = await repo.clone_bare()

    assert result is True
    mock_execute_git.assert_awaited_once_with(
        "clone",
        "--bare",
        "--progress",
        "http://a.b/org/c.git",
        str(repo.bare_repo_path),
        cwd=tmp_path,
        gitconfig=None,
    )


async def test_managed_repo_clone_bare_exists(
    tmp_path: Path, mock_execute_git: AsyncMock, monkeypatch
):
    """Test clone_bare when the repository already exists."""
    repo = ManagedGitRepo("http://a.b/org/c.git", tmp_path)
    mock_execute_git.return_value = CompletedProcess(
        args=[], returncode=0, stdout="", stderr=""
    )
    # Simulate repo exists
    monkeypatch.setattr(Path, "exists", lambda self: True)

    await repo.clone_bare()
    mock_execute_git.assert_awaited_once()


async def test_managed_repo_clone_bare_failure(
    tmp_path: Path, mock_execute_git: AsyncMock, monkeypatch
):
    """Test clone_bare when the git command fails."""
    repo = ManagedGitRepo("http://a.b/org/c.git", tmp_path)
    # Simulate repo does not exist
    monkeypatch.setattr(Path, "exists", lambda self: False)
    mock_execute_git.side_effect = RuntimeError("Git clone failed")

    result = await repo.clone_bare()
    assert result is False


async def test_managed_repo_create_worktree_success(
    tmp_path: Path, mock_execute_git: AsyncMock, monkeypatch
):
    """Test create_worktree successfully creates a worktree."""
    mock_execute_git.return_value = CompletedProcess(
        args=[], returncode=0, stdout="", stderr=""
    )
    repo = ManagedGitRepo("http://a.b/org/c.git", tmp_path)
    # Simulate bare repo exists
    monkeypatch.setattr(Path, "exists", lambda self: True)
    target_dir = tmp_path / "worktree"

    await repo.create_worktree(target_dir, "main")

    mock_execute_git.assert_awaited_once_with(
        "clone",
        "--local",
        "--branch",
        "main",
        str(repo.bare_repo_path),
        str(target_dir),
        cwd=target_dir.parent,
        gitconfig=None,
    )


async def test_managed_repo_create_worktree_with_options(
    tmp_path: Path, mock_execute_git: AsyncMock, monkeypatch
):
    """Test create_worktree with additional clone options."""
    mock_execute_git.return_value = CompletedProcess(
        args=[], returncode=0, stdout="", stderr=""
    )
    repo = ManagedGitRepo("http://a.b/org/c.git", tmp_path)
    # Simulate bare repo exists
    monkeypatch.setattr(Path, "exists", lambda self: True)
    target_dir = tmp_path / "worktree"

    await repo.create_worktree(target_dir, "develop", options=["--depth", "1"])

    mock_execute_git.assert_awaited_once_with(
        "clone",
        "--local",
        "--branch",
        "develop",
        "--depth",
        "1",
        str(repo.bare_repo_path),
        str(target_dir),
        cwd=target_dir.parent,
        gitconfig=None,
    )


async def test_managed_repo_create_worktree_no_bare_repo(
    tmp_path: Path, mock_execute_git: AsyncMock, monkeypatch
):
    """Test create_worktree fails if the bare repository does not exist."""
    repo = ManagedGitRepo("http://a.b/org/c.git", tmp_path)
    # Simulate bare repo does not exist
    monkeypatch.setattr(Path, "exists", lambda self: False)
    target_dir = tmp_path / "worktree"

    with pytest.raises(FileNotFoundError, match="Bare repository does not exist"):
        await repo.create_worktree(target_dir, "main")

    mock_execute_git.assert_not_awaited()


async def test_managed_repo_create_worktree_not_local(
    tmp_path: Path, mock_execute_git: AsyncMock, monkeypatch
):
    """Test create_worktree without the --local flag."""
    mock_execute_git.return_value = CompletedProcess(
        args=[], returncode=0, stdout="", stderr=""
    )
    repo = ManagedGitRepo("http://a.b/org/c.git", tmp_path)
    # Simulate bare repo exists
    monkeypatch.setattr(Path, "exists", lambda self: True)
    target_dir = tmp_path / "worktree"

    # Explicitly call with is_local=False
    await repo.create_worktree(target_dir, "main", is_local=False)

    mock_execute_git.assert_awaited_once_with(
        "clone",
        "--branch",
        "main",
        str(repo.bare_repo_path),
        str(target_dir),
        cwd=target_dir.parent,
        gitconfig=None,
    )


def test_managed_git_repo_repr(tmp_path: Path):
    """Test the __repr__ method of ManagedGitRepo."""
    remote_url = "https://github.com/test/repo.git"
    repo_model = Repo(remote_url)
    repo = ManagedGitRepo(remote_url, tmp_path)
    expected_repr = (
        f"{repo.__class__.__name__}(remote_url='{remote_url}', "
        f"bare_repo_path='{tmp_path / repo_model.slug!s}')"
    )
    assert repr(repo) == expected_repr


def test_managed_git_repo_remote_url_property(tmp_path: Path):
    """Test the remote_url property of ManagedGitRepo."""
    # Use a short-form URL to ensure the underlying Repo model is used correctly
    short_url = "gh://my-org/my-repo"
    repo = ManagedGitRepo(short_url, tmp_path)
    # The property should return the full, canonical URL
    assert repo.remote_url == "https://github.com/my-org/my-repo.git"


@pytest.mark.parametrize(
    "repo_input",
    [
        "https://github.com/my-org/my-repo.git",
        Repo("gh://my-org/my-repo"),
    ],
)
def test_managed_git_repo_slug_property(tmp_path: Path, repo_input):
    """Test the slug property of ManagedGitRepo for str and Repo inputs."""
    repo = ManagedGitRepo(repo_input, tmp_path)
    # The slug should be a filesystem-safe version of the canonical URL
    expected_slug = "https___github_com_my_org_my_repo_git"
    assert repo.slug == expected_slug


def test_managed_git_repo_permanent_root_property(tmp_path: Path):
    """Test the permanent_root property of ManagedGitRepo."""
    remote_url = "https://github.com/test/repo.git"
    permanent_root = tmp_path / "permanent_repos"
    repo = ManagedGitRepo(remote_url, permanent_root)
    assert repo.permanent_root == permanent_root


def test_managed_git_repo_invalid_repo_type(tmp_path: Path):
    """ManagedGitRepo should reject unsupported repo types with TypeError."""

    with pytest.raises(TypeError, match="remote_url must be a string or Repo instance"):
        ManagedGitRepo(123, tmp_path)  # type: ignore[arg-type]


async def test_fetch_updates_success(
    tmp_path: Path, mock_execute_git: AsyncMock, monkeypatch
):
    """Test fetch_updates successfully fetches updates."""
    mock_execute_git.return_value = CompletedProcess(
        args=[], returncode=0, stdout="", stderr=""
    )
    repo = ManagedGitRepo("http://a.b/org/c.git", tmp_path)
    # Simulate bare repo exists
    monkeypatch.setattr(Path, "exists", lambda self: True)

    result = await repo.fetch_updates()

    assert result is True
    mock_execute_git.assert_awaited_once()


async def test_fetch_updates_no_repo(
    tmp_path: Path, mock_execute_git: AsyncMock, monkeypatch
):
    """Test fetch_updates fails if the bare repository does not exist."""
    repo = ManagedGitRepo("http://a.b/org/c.git", tmp_path)
    # Simulate bare repo does not exist
    monkeypatch.setattr(Path, "exists", lambda self: False)

    result = await repo.fetch_updates()

    assert result is False
    mock_execute_git.assert_not_awaited()


async def test_fetch_updates_failure(
    tmp_path: Path, mock_execute_git: AsyncMock, monkeypatch
):
    """Test fetch_updates when the git command fails."""
    repo = ManagedGitRepo("http://a.b/org/c.git", tmp_path)
    # Simulate bare repo exists
    monkeypatch.setattr(Path, "exists", lambda self: True)
    mock_execute_git.side_effect = RuntimeError("Git fetch failed")

    result = await repo.fetch_updates()

    assert result is False


async def test_managed_repo_clone_bare_already_processed(
    tmp_path: Path, mock_execute_git: AsyncMock, monkeypatch
):
    """Test clone_bare when the repository has been processed in this run."""
    mock_execute_git.return_value = CompletedProcess(
        args=[], returncode=0, stdout="", stderr=""
    )
    repo = ManagedGitRepo("http://a.b/org/c.git", tmp_path)
    # Simulate repo does not exist for the first call
    monkeypatch.setattr(Path, "exists", lambda self: False)

    # First call, should perform a clone
    result1 = await repo.clone_bare()

    assert result1 is True
    mock_execute_git.assert_awaited_once_with(
        "clone",
        "--bare",
        "--progress",
        "http://a.b/org/c.git",
        str(repo.bare_repo_path),
        cwd=tmp_path,
        gitconfig=None,
    )

    # Second call, should do nothing because it's already processed
    result2 = await repo.clone_bare()

    assert result2 is True
    # The mock should still have only been called once
    mock_execute_git.assert_awaited_once()


async def test_ls_tree_no_repo(
    tmp_path: Path, mock_execute_git: AsyncMock, monkeypatch
):
    """Test ls_tree when the bare repository does not exist."""
    repo = ManagedGitRepo("http://a.b/org/c.git", tmp_path)
    # Simulate bare repo does not exist
    monkeypatch.setattr(Path, "exists", lambda self: False)

    with patch.object(git_module.log, "warning") as mock_log_warning:
        result = await repo.ls_tree("main")

        assert result == []
        mock_log_warning.assert_called_once_with(
            "Cannot run ls-tree: Bare repository does not exist at %s",
            repo.bare_repo_path,
        )
        mock_execute_git.assert_not_awaited()


async def test_ls_tree_success_recursive(
    tmp_path: Path, mock_execute_git: AsyncMock, monkeypatch
):
    """Test ls_tree successfully lists files recursively."""
    repo = ManagedGitRepo("http://a.b/org/c.git", tmp_path)
    monkeypatch.setattr(Path, "exists", lambda self: True)
    mock_execute_git.return_value = CompletedProcess(
        args=[], returncode=0, stdout="file1.txt\ndir/file2.txt", stderr=""
    )

    result = await repo.ls_tree("main")

    assert result == ["file1.txt", "dir/file2.txt"]
    mock_execute_git.assert_awaited_once_with(
        "ls-tree",
        "--name-only",
        "-r",
        "main",
        cwd=repo.bare_repo_path,
        gitconfig=None,
    )


async def test_ls_tree_success_non_recursive(
    tmp_path: Path, mock_execute_git: AsyncMock, monkeypatch
):
    """Test ls_tree successfully lists files non-recursively."""
    repo = ManagedGitRepo("http://a.b/org/c.git", tmp_path)
    monkeypatch.setattr(Path, "exists", lambda self: True)
    mock_execute_git.return_value = CompletedProcess(
        args=[], returncode=0, stdout="file1.txt", stderr=""
    )

    result = await repo.ls_tree("main", recursive=False)

    assert result == ["file1.txt"]
    mock_execute_git.assert_awaited_once_with(
        "ls-tree",
        "--name-only",
        "main",
        cwd=repo.bare_repo_path,
        gitconfig=None,
    )


async def test_ls_tree_empty_output(
    tmp_path: Path, mock_execute_git: AsyncMock, monkeypatch
):
    """Test ls_tree handles empty stdout correctly."""
    repo = ManagedGitRepo("http://a.b/org/c.git", tmp_path)
    monkeypatch.setattr(Path, "exists", lambda self: True)
    mock_execute_git.return_value = CompletedProcess(
        args=[], returncode=0, stdout="", stderr=""
    )

    result = await repo.ls_tree("main")

    assert result == []


async def test_ls_tree_command_failure(
    tmp_path: Path, mock_execute_git: AsyncMock, monkeypatch
):
    """Test ls_tree handles a RuntimeError from execute_git_command."""
    repo = ManagedGitRepo("http://a.b/org/c.git", tmp_path)
    monkeypatch.setattr(Path, "exists", lambda self: True)
    error = RuntimeError("Git command failed")
    mock_execute_git.side_effect = error

    with patch.object(git_module.log, "error") as mock_log_error:
        result = await repo.ls_tree("develop")

        assert result == []
        mock_log_error.assert_called_once_with(
            "Failed to run ls-tree on branch '%s' in '%s': %s",
            "develop",
            repo.slug,
            error,
        )
