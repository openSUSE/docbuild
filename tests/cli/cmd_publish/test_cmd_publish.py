"""Tests for the docbuild publish command."""

from unittest.mock import AsyncMock, Mock, patch

from click.testing import CliRunner

from docbuild.cli.cmd_cli import cli
from docbuild.cli.cmd_publish.cmd_run import run
from docbuild.cli.context import DocBuildContext
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

    with patch(
        "docbuild.cli.cmd_publish.cmd_run.stage_server_root_files",
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
        patch(
            "docbuild.cli.cmd_publish.cmd_run.collect_publish_paths",
            new_callable=AsyncMock,
            return_value=["sles/16.0/en-us/html"],
        ),
        patch(
            "docbuild.cli.cmd_publish.cmd_run.publish_deliverables",
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
