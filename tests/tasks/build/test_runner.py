"""Unit tests for docbuild.tasks.build.runner."""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from lxml import etree  # type: ignore
import pytest

from docbuild.models.deliverable import Deliverable
from docbuild.models.doctype import Doctype
import docbuild.tasks.build.runner as build_runner
from docbuild.tasks.build.runner import (
    build_format,
    process,
    process_deliverable_build,
    process_doctype,
)


class SortableMock(Mock):
    """A Mock that supports sorting by the full_id attribute."""

    def __lt__(self, other: object) -> bool:
        return str(getattr(self, "full_id", "")) < str(getattr(other, "full_id", ""))


@pytest.fixture
def empty_xml_root() -> etree._ElementTree:
    """Return a minimal empty ElementTree."""
    return etree.ElementTree(etree.fromstring("<docservconfig/>"))


@pytest.mark.asyncio
async def test_build_format_no_dcfile(tmp_path: Path) -> None:
    """Test that missing DC file safely raises error."""
    mock_d = Mock(spec=Deliverable, full_id="test:DC")
    mock_d.xml.dcfile = None

    with pytest.raises(AssertionError, match=r"Deliverable must have a DC file\."):
        await build_format(mock_d, "html", tmp_path, tmp_path, "daps -d {{dcfile}} html")


@pytest.mark.asyncio
async def test_build_format_failure(tmp_path: Path) -> None:
    """Test handling of a failed daps subprocess."""
    mock_d = Mock(spec=Deliverable, full_id="test:DC")
    mock_d.xml.dcfile = "DC-test"

    with patch.object(build_runner, "run_command", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="Build crashed")

        success, err = await build_format(
            mock_d, "html", tmp_path, tmp_path, "daps -d {{dcfile}} --builddir {{builddir}} html"
        )
        assert success is False
        assert err == "Build crashed"


@pytest.mark.asyncio
@patch("docbuild.tasks.build.runner.ManagedGitRepo", autospec=True)
async def test_process_deliverable_build_success(
    mock_mgr_class: Mock, tmp_path: Path
) -> None:
    """Test successful build execution for enabled formats."""
    mock_deliverable = Mock(
        spec=Deliverable,
        full_id="sles/15:TEST",
        subdir="subdir",
        format={"html": True, "pdf": False},
        branch="main",
    )
    mock_deliverable.xml.dcfile = "DC-test"
    mock_deliverable.git.url = "https://git.test"
    mock_deliverable.make_safe_name.return_value = "safe_sles_15_TEST"

    # Mock the worktree creation
    mock_mgr_instance = mock_mgr_class.return_value
    mock_mgr_instance.create_worktree = AsyncMock()

    daps_tmpls = {"html": "daps -d {{dcfile}} --builddir {{builddir}} html"}

    with patch.object(
        build_runner, "run_command", new_callable=AsyncMock
    ) as mock_run:
        mock_run.return_value = Mock(returncode=0, stdout="Build OK", stderr="")

        success, deliverable = await process_deliverable_build(
            mock_deliverable, tmp_path, tmp_path, tmp_path, daps_tmpls
        )

        assert success is True
        assert deliverable == mock_deliverable
        mock_mgr_instance.create_worktree.assert_called_once()
        mock_run.assert_called_once()


@pytest.mark.asyncio
async def test_process_doctype_build(
    empty_xml_root: etree._ElementTree, tmp_path: Path
) -> None:
    """Test process_doctype pipeline for build task."""
    doctype = Doctype.from_str("sles/15/en-us")
    d1 = SortableMock(
        spec=Deliverable,
        full_id="sles/15:A",
        subdir="",
        format={"html": True},
    )
    d1.xml.is_dc = True

    daps_tmpls = {"html": "daps html"}

    with (
        patch.object(build_runner, "get_deliverable_from_doctype", return_value=[d1]),
        patch.object(build_runner, "process_deliverable_build", new_callable=AsyncMock) as mock_build,
        patch.object(build_runner, "update_repositories", new_callable=AsyncMock) as mock_update,
    ):
        mock_build.return_value = (True, d1)
        failed = await process_doctype(
            root=empty_xml_root,
            doctype=doctype,
            repo_dir=tmp_path,
            tmp_repo_dir=tmp_path,
            tmp_build_base_dir=tmp_path,
            max_workers=2,
            daps_tmpls=daps_tmpls,
            skip_repo_update=False,
        )

        assert failed == []
        mock_build.assert_called_once()
        mock_update.assert_called_once()


@pytest.mark.asyncio
async def test_process_entry_point(tmp_path: Path) -> None:
    """Test the main process() orchestration function."""
    doctype = Doctype.from_str("sles/15/en-us")
    daps_tmpls = {"html": "daps html"}

    with (
        patch.object(build_runner, "parse_portal_config", new_callable=AsyncMock),
        patch.object(build_runner, "process_doctype", new_callable=AsyncMock) as mock_pd,
    ):
        mock_pd.return_value = []
        result = await process(tmp_path, tmp_path, tmp_path, tmp_path, 1, [doctype], daps_tmpls)
        assert result == 0

        mock_pd.return_value = [Mock(spec=Deliverable)]
        result = await process(tmp_path, tmp_path, tmp_path, tmp_path, 1, [doctype], daps_tmpls)
        assert result == 1
