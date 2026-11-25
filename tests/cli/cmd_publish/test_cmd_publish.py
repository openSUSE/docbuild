"""Tests for the docbuild publish command."""

from unittest.mock import AsyncMock, Mock, patch

from click.testing import CliRunner
import pytest
from rich.console import Console

from docbuild.cli.cmd_cli import cli
from docbuild.cli.cmd_publish import cmd_run
from docbuild.cli.cmd_publish.cmd_run import run
from docbuild.cli.context import DocBuildContext
from docbuild.cli.theme import DOCBUILD_THEME
from docbuild.utils.display import ItemState, get_live_manager
from docbuild.utils.sync import RsyncOptions


def test_publish_help() -> None:
    """Test publish --help output."""
    runner = CliRunner()
    result = runner.invoke(cli, ["publish", "--help"])
    assert result.exit_code == 0
    assert "Publish documentation deliverables" in result.output
    assert "run" in result.output


def test_publish_run_help() -> None:
    """Test publish run --help contains dry-run flag."""
    runner = CliRunner()
    result = runner.invoke(cli, ["publish", "run", "--help"])
    assert result.exit_code == 0
    assert "-n, --dry-run" in result.output
    assert "-L, --live" in result.output


def test_publish_run_missing_remote() -> None:
    """Test publish run aborts if remote server and path are not configured."""
    runner = CliRunner()

    mock_ctx = Mock(spec=DocBuildContext)
    mock_ctx.envconfig.remote.server = None
    mock_ctx.envconfig.remote.path = None

    result = runner.invoke(run, ["sles/16.0/en-us"], obj=mock_ctx)
    assert result.exit_code != 0
    assert "The [remote] section is not configured" in result.output


def test_publish_run_staging_failure(tmp_path) -> None:
    """Test publish run aborts with ClickException if staging fails."""
    runner = CliRunner()

    mock_ctx = Mock(spec=DocBuildContext)
    mock_ctx.envconfig.remote.server = "doc@example.com"
    mock_ctx.envconfig.remote.path = "/srv/docs"
    mock_ctx.envconfig.paths.target.target_base_dir = tmp_path / "target"
    mock_ctx.envconfig.paths.target.target_dir_dyn = "{product}"
    mock_ctx.envconfig.paths.server_rootfiles_dir = tmp_path / "server_files"
    mock_ctx.envconfig.rsync.to_options.return_value = RsyncOptions()
    (tmp_path / "server_files").mkdir()

    with patch.object(
        cmd_run,
        "stage_server_root_files",
        side_effect=RuntimeError("Disk write error"),
    ):
        result = runner.invoke(run, ["sles/16.0/en-us"], obj=mock_ctx)
        assert result.exit_code != 0
        assert "Disk write error" in result.output


def test_publish_run_dry_run(tmp_path) -> None:
    """Test publish run with --dry-run option."""
    runner = CliRunner()

    mock_ctx = Mock(spec=DocBuildContext)
    mock_ctx.envconfig.remote.server = "doc@example.com"
    mock_ctx.envconfig.remote.path = "/srv/docs"
    mock_ctx.envconfig.paths.target.target_base_dir = tmp_path / "target"
    mock_ctx.envconfig.paths.target.target_dir_dyn = "{product}"
    mock_ctx.envconfig.paths.server_rootfiles_dir = None
    mock_ctx.envconfig.rsync.to_options.return_value = RsyncOptions()
    mock_ctx.main_portal_config = tmp_path / "portal.xml"

    with (
        patch.object(
            cmd_run,
            "collect_publish_paths",
            new_callable=AsyncMock,
            return_value=["sles/16.0/en-us/html"],
        ),
        patch.object(
            cmd_run,
            "publish_deliverables",
            new_callable=AsyncMock,
            return_value=0,
        ) as mock_pub,
    ):
        result = runner.invoke(run, ["--dry-run", "sles/16.0/en-us"], obj=mock_ctx)
        assert result.exit_code == 0
        assert "[DRY RUN]" in result.output
        assert "Dry run completed successfully!" in result.output

        # Verify rsync_options had dry_run set to True
        mock_pub.assert_called_once()
        _, kwargs = mock_pub.call_args
        assert kwargs["rsync_options"].dry_run is True


@pytest.mark.parametrize(
    ("flags", "returncode"), [([], 0), (["-L"], 0), (["--live"], 23)]
)
def test_publish_progress(tmp_path, monkeypatch, flags, returncode):
    monkeypatch.setattr(
        cmd_run, "console", Console(theme=DOCBUILD_THEME, force_terminal=True)
    )
    ctx = Mock(spec=DocBuildContext)
    ctx.envconfig.remote.server = "localhost"
    ctx.envconfig.remote.path = "/docs"
    paths = ctx.envconfig.paths
    paths.target.target_base_dir = tmp_path / "target"
    paths.target.target_dir_dyn = "{product}"
    paths.main_portal_config = tmp_path / "portal.xml"
    paths.main_portal_config.write_text("<docservconfig/>")
    paths.server_rootfiles_dir = tmp_path / "server-files"
    paths.server_rootfiles_dir.mkdir()
    (paths.server_rootfiles_dir / "robots.txt").touch()
    ctx.envconfig.rsync.to_options.return_value = RsyncOptions()

    manager = None

    async def rsync(source, dest, *, content_only, options):
        nonlocal manager
        if options.files_from is None:
            return Mock(returncode=0)  # Local staging
        manager = get_live_manager()
        (transfer,) = manager.stages
        assert list(transfer.running.values()) == [dest]
        assert not transfer.counts
        assert options.files_from.read_text() == "robots.txt\n"
        return Mock(returncode=returncode, stderr="test transfer error")

    monkeypatch.setattr("docbuild.tasks.publish.rsync", rsync)
    result = CliRunner().invoke(run, [*flags, "sles/16.0/en-us"], input="y\n", obj=ctx)
    assert result.exit_code == returncode, result.exception
    assert "Do you want to continue? [y/N]" in result.output
    assert ("Collect publish paths" in result.output) == bool(flags)
    assert ("Publish deliverables" in result.output) == bool(flags)
    assert "robots.txt" in result.output
    assert manager is not None
    transfer = manager.stages[-1]
    outcome = ItemState.FAILED if returncode else ItemState.SUCCEEDED
    assert transfer.counts == {outcome: 1}
    assert not transfer.running
    assert get_live_manager() is None
