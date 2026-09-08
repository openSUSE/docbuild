"""Unit tests for docbuild.utils.sync."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

import docbuild.utils.sync as sync_mod
from docbuild.utils.sync import RsyncOptions, is_remote_path, rsync


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("user@host:/var/www", True),
        ("host:/var/www", True),
        ("host:relative/path", True),
        ("host:", True),
        ("user@host::module/path", True),
        ("host::module", True),
        ("rsync://user@host/module/path", True),
        ("rsync://host/module", True),
        ("/var/www/docs", False),
        ("relative/path", False),
        ("docs", False),
        ("./dir/with:colon", False),
        ("/dir/with:colon/file", False),
        (Path("/local/path"), False),
    ],
    ids=[
        "ssh_with_user",
        "ssh_host_only",
        "ssh_relative_path",
        "ssh_host_colon_only",
        "daemon_with_user",
        "daemon_host_only",
        "url_with_user",
        "url_host_only",
        "local_absolute",
        "local_relative",
        "local_single_dir",
        "local_relative_with_colon",
        "local_absolute_with_colon",
        "local_pathlib_object",
    ],
)
def test_is_remote_path(path: str | Path, expected: bool) -> None:
    """Test remote path detection."""
    assert is_remote_path(path) is expected


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
        (
            RsyncOptions(exclude=["*.log", ".git"]),
            ["-a", "--exclude", "*.log", "--exclude", ".git"],
        ),
    ],
    ids=["defaults", "custom_flags", "exclude_list"],
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

    mock_run_command.reset_mock()

    # Root directory / should not be stripped to empty string
    await rsync("/", "target_dir", content_only=False)
    mock_run_command.assert_called_once_with(["rsync", "-a", "/", "target_dir"])


@pytest.mark.asyncio
@patch.object(sync_mod, "run_command", new_callable=AsyncMock)
async def test_rsync_with_pathlib(mock_run_command: AsyncMock) -> None:
    """Test execution using Path objects."""
    await rsync(Path("src"), Path("dest"), content_only=True)

    mock_run_command.assert_called_once_with(["rsync", "-a", "src/", "dest"])


@pytest.mark.asyncio
@patch.object(sync_mod, "run_command", new_callable=AsyncMock)
@pytest.mark.parametrize(
    ("source", "content_only", "expected_source_arg"),
    [
        ("user@host:/srv/docs/", None, "user@host:/srv/docs/"),
        ("user@host:/srv/docs", None, "user@host:/srv/docs"),
        ("user@host:/srv/docs", True, "user@host:/srv/docs/"),
        ("user@host:/srv/docs/", True, "user@host:/srv/docs/"),
        ("user@host:/srv/docs/", False, "user@host:/srv/docs"),
        ("user@host:/srv/docs", False, "user@host:/srv/docs"),
        ("host:/", None, "host:/"),
        ("host:/", True, "host:/"),
        ("host:/", False, "host:/"),
    ],
    ids=[
        "inferred_trailing_slash",
        "inferred_no_slash",
        "explicit_true_without_slash",
        "explicit_true_with_slash",
        "explicit_false_with_slash",
        "explicit_false_without_slash",
        "remote_root_inferred",
        "remote_root_explicit_true",
        "remote_root_explicit_false",
    ],
)
async def test_rsync_remote_source(
    mock_run_command: AsyncMock,
    source: str,
    content_only: bool | None,
    expected_source_arg: str,
) -> None:
    """Test rsync with remote source under various content_only settings."""
    await rsync(source, "local_dest", content_only=content_only)
    mock_run_command.assert_called_once_with(
        ["rsync", "-a", expected_source_arg, "local_dest"]
    )


@pytest.mark.asyncio
@patch.object(sync_mod, "run_command", new_callable=AsyncMock)
@pytest.mark.parametrize(
    ("target", "expected_target_arg"),
    [
        ("user@host:/srv/docs", "user@host:/srv/docs"),
        ("user@host:/srv/docs/", "user@host:/srv/docs/"),
        ("rsync://user@host/module/docs", "rsync://user@host/module/docs"),
    ],
    ids=["ssh_target", "ssh_target_trailing_slash", "daemon_target"],
)
async def test_rsync_remote_target(
    mock_run_command: AsyncMock,
    target: str,
    expected_target_arg: str,
) -> None:
    """Test rsync execution with remote target."""
    await rsync("source_dir", target, content_only=True)
    mock_run_command.assert_called_once_with(
        ["rsync", "-a", "source_dir/", expected_target_arg]
    )


@pytest.mark.asyncio
async def test_rsync_both_remote_raises() -> None:
    """Test that specifying both source and target as remote raises ValueError."""
    with pytest.raises(
        ValueError, match=r"Both source and target cannot be remote paths\."
    ):
        await rsync("user@host1:/src", "user@host2:/dest")

