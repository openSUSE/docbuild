"""Unit tests for docbuild.utils.sync."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

import docbuild.utils.sync as sync_mod
from docbuild.utils.sync import RsyncOptions, rsync


@pytest.mark.parametrize(
    ("options", "expected"),
    [
        (
            RsyncOptions(),
            ["-a"],
        ),
        (
            RsyncOptions(
                archive=False,
                compress=True,
                delete=True,
                dry_run=True,
                verbose=True,
                partial=True,
                extra_args=["--exclude=*.tmp"],
            ),
            ["-z", "--delete", "--dry-run", "-v", "--partial", "--exclude=*.tmp"],
        ),
    ],
    ids=["defaults", "custom_flags"],
)
def test_rsync_options_to_args(options: RsyncOptions, expected: list[str]) -> None:
    """Test rsync options generation."""
    assert options.to_args() == expected


@pytest.mark.asyncio
@patch.object(sync_mod, "run_command", new_callable=AsyncMock)
async def test_rsync_basic(mock_run_command: AsyncMock) -> None:
    """Test rsync execution with basic paths."""
    await rsync("source_dir", "target_dir")

    mock_run_command.assert_called_once_with(["rsync", "-a", "source_dir", "target_dir"])


@pytest.mark.asyncio
@patch.object(sync_mod, "run_command", new_callable=AsyncMock)
async def test_rsync_content_only_inferred(mock_run_command: AsyncMock) -> None:
    """Test trailing slash inference."""
    await rsync("source_dir/", "target_dir")

    mock_run_command.assert_called_once_with(["rsync", "-a", "source_dir/", "target_dir"])


@pytest.mark.asyncio
@patch.object(sync_mod, "run_command", new_callable=AsyncMock)
async def test_rsync_content_only_explicit(mock_run_command: AsyncMock) -> None:
    """Test explicit content_only override."""
    # Even without trailing slash in input, it should be appended
    await rsync("source_dir", "target_dir", content_only=True)
    mock_run_command.assert_called_once_with(["rsync", "-a", "source_dir/", "target_dir"])

    mock_run_command.reset_mock()

    # Even with trailing slash in input, if False, it should NOT append
    await rsync("source_dir/", "target_dir", content_only=False)
    mock_run_command.assert_called_once_with(["rsync", "-a", "source_dir", "target_dir"])


@pytest.mark.asyncio
@patch.object(sync_mod, "run_command", new_callable=AsyncMock)
async def test_rsync_with_pathlib(mock_run_command: AsyncMock) -> None:
    """Test execution using Path objects."""
    await rsync(Path("src"), Path("dest"), content_only=True)

    mock_run_command.assert_called_once_with(["rsync", "-a", "src/", "dest"])
