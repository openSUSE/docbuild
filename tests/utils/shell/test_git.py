"""Test the git repo utils."""
import asyncio
from pathlib import Path
import subprocess
from unittest.mock import AsyncMock, patch

import pytest

from docbuild.utils.shell.git import clone_from_repo


async def test_clone_from_repo_success(tmp_path: Path):
    """Test that clone_from_repo successfully clones a repo."""
    repo_path = tmp_path / "repo"
    worktree_dir = tmp_path / "worktree"
    branch = "main"

    with patch.object(asyncio, "create_subprocess_exec") as mock_exec:
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0
        mock_exec.return_value = mock_process

        result = await clone_from_repo(repo_path, worktree_dir, branch)

        assert result == worktree_dir
        mock_exec.assert_called_once_with(
            "git",
            "clone",
            "--local",
            "--branch",
            branch,
            str(repo_path),
            str(worktree_dir),
            stdout=None,
            stdin=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )


async def test_clone_from_repo_failure(tmp_path: Path):
    """Test that clone_from_repo raises an exception on failure."""
    repo_path = tmp_path / "repo"
    worktree_dir = tmp_path / "worktree"
    branch = "main"
    error_message = "fatal: repository not found"

    with patch.object(asyncio, "create_subprocess_exec") as mock_exec:
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"", error_message.encode())
        mock_process.returncode = 1
        mock_exec.return_value = mock_process

        with pytest.raises(RuntimeError) as excinfo:
            await clone_from_repo(repo_path, worktree_dir, branch)

        assert error_message in str(excinfo.value)


async def test_clone_from_repo_with_options(tmp_path: Path):
    """Test that clone_from_repo correctly uses additional options."""
    repo_path = tmp_path / "repo"
    worktree_dir = tmp_path / "worktree"
    branch = "main"
    options = ["--depth", "1"]

    with patch.object(asyncio, "create_subprocess_exec") as mock_exec:
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0
        mock_exec.return_value = mock_process

        await clone_from_repo(
            repo_path, worktree_dir, branch, options=options, is_local=False
        )

        mock_exec.assert_called_once_with(
            "git",
            "clone",
            "--branch",
            branch,
            "--depth",
            "1",
            str(repo_path),
            str(worktree_dir),
            stdout=None,
            stdin=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )


async def test_clone_from_repo_no_local(tmp_path: Path):
    """Test that clone_from_repo works without the --local option."""
    repo_path = tmp_path / "repo"
    worktree_dir = tmp_path / "worktree"
    branch = "main"

    with patch.object(asyncio, "create_subprocess_exec") as mock_exec:
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0
        mock_exec.return_value = mock_process

        await clone_from_repo(repo_path, worktree_dir, branch, is_local=False)

        mock_exec.assert_called_once_with(
            "git",
            "clone",
            "--branch",
            branch,
            str(repo_path),
            str(worktree_dir),
            stdout=None,
            stdin=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )


async def test_clone_from_repo_failure_no_stderr(tmp_path: Path):
    """Test that clone_from_repo raises an exception on failure without stderr."""
    repo_path = tmp_path / "repo"
    worktree_dir = tmp_path / "worktree"
    branch = "main"

    with patch.object(asyncio, "create_subprocess_exec") as mock_exec:
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"", b"")  # No stderr
        mock_process.returncode = 1
        mock_exec.return_value = mock_process

        with pytest.raises(RuntimeError) as excinfo:
            await clone_from_repo(repo_path, worktree_dir, branch)

        assert "()" not in str(excinfo.value)
