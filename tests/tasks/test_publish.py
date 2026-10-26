"""Unit tests for docbuild.tasks.publish."""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from docbuild.models.deliverable import Deliverable
from docbuild.models.doctype import Doctype
from docbuild.tasks.publish import (
    collect_publish_paths,
    publish_deliverables,
    stage_server_root_files,
)
from docbuild.utils.sync import RsyncOptions


@pytest.mark.asyncio
async def test_stage_server_root_files_missing(tmp_path: Path) -> None:
    """Verify non-existent server root directory safely returns False."""
    res = await stage_server_root_files(tmp_path / "nonexistent", tmp_path / "target")
    assert res is False


@pytest.mark.asyncio
async def test_stage_server_root_files_success(tmp_path: Path) -> None:
    """Verify server root directory is synced to target base dir."""
    server_dir = tmp_path / "server_files"
    server_dir.mkdir()
    target_dir = tmp_path / "target"

    with patch("docbuild.tasks.publish.rsync", new_callable=AsyncMock) as mock_rsync:
        mock_rsync.return_value = Mock(returncode=0)
        res = await stage_server_root_files(server_dir, target_dir)
        assert res is True
        mock_rsync.assert_called_once()


@pytest.mark.asyncio
async def test_collect_publish_paths(tmp_path: Path) -> None:
    """Verify relative publish paths are collected based on deliverables."""
    portal_config = tmp_path / "portal.xml"
    portal_config.write_text("<docservconfig/>", encoding="utf-8")

    doctype = Doctype.from_str("sles/16.0/en-us")
    mock_d = Mock(spec=Deliverable)
    mock_d.xml.is_dc = True
    mock_d.xml.product_id = "sles"
    mock_d.xml.docset_path = "16.0"
    mock_d.xml.lang = "en-us"
    mock_d.format = {"html": True, "pdf": False}

    target_base = tmp_path / "target"
    html_dir = target_base / "sles/16.0/en-us/html"
    html_dir.mkdir(parents=True)

    with (
        patch("docbuild.tasks.publish.parse_portal_config", new_callable=AsyncMock),
        patch("docbuild.tasks.publish.get_deliverable_from_doctype", return_value=[mock_d]),
    ):
        paths = await collect_publish_paths(
            portal_config=portal_config,
            doctypes=[doctype],
            target_base_dir=target_base,
            target_dir_dyn="{product}/{docset}/{lang}",
            include_server_files=False,
        )

    assert "sles/16.0/en-us/html" in paths


@pytest.mark.asyncio
async def test_publish_deliverables(tmp_path: Path) -> None:
    """Verify rsync is called with files-from temporary file."""
    with patch("docbuild.tasks.publish.rsync", new_callable=AsyncMock) as mock_rsync:
        mock_rsync.return_value = Mock(returncode=0)
        ret = await publish_deliverables(
            target_base_dir=tmp_path,
            remote_server="doc@example.com",
            remote_path="/srv/docs",
            paths_to_sync=["sles/16.0/en-us/html"],
            rsync_options=RsyncOptions(),
        )
        assert ret == 0
        assert mock_rsync.called
        args, kwargs = mock_rsync.call_args
        assert args[0] == tmp_path
        assert args[1] == "doc@example.com:/srv/docs"
        assert kwargs["options"].files_from is not None
