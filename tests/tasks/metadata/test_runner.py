"""Tests for the docbuild.tasks.metadata.runner module."""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from lxml import etree
import pytest

from docbuild.models.deliverable import Deliverable
from docbuild.models.doctype import Doctype
from docbuild.tasks.metadata.runner import (
    _execute_build_pipeline,
    _gather_build_tasks,
    get_deliverable_worker_limit,
    process,
)


def test_get_deliverable_worker_limit() -> None:
    """Test the get_deliverable_worker_limit function."""
    assert get_deliverable_worker_limit(4, 10) == 4
    assert get_deliverable_worker_limit(4, 2) == 2
    assert get_deliverable_worker_limit(4, 0) == 1
    assert get_deliverable_worker_limit(4, -1) == 1
    assert get_deliverable_worker_limit(1, 10) == 1


class SortableMock(Mock):
    """A mock that can be sorted for testing."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.full_id = f"mock_{id(self)}"

    def __lt__(self, other: object) -> bool:
        return self.full_id < getattr(other, "full_id", "")


@pytest.fixture
def empty_xml_root() -> etree._ElementTree:
    """Return an empty parsed XML element tree."""
    return etree.ElementTree(etree.Element("portal"))


class TestGatherBuildTasks:
    """Tests for the _gather_build_tasks phase."""

    @patch("docbuild.tasks.metadata.runner.get_deliverable_from_doctype")
    def test_gathers_and_deduplicates_deliverables(
        self, mock_get_deliverables: Mock, empty_xml_root: etree._ElementTree
    ) -> None:
        """Verify phase 1 dependency discovery and xref unwrapping."""
        doctype = Doctype.from_str("sles/15/en-us")

        # Create normal deliverable
        d1 = SortableMock(spec=Deliverable)
        d1.full_id = "d1"
        d1.xml.is_xref = False

        # Create xref pointing to a deliverable
        d2 = SortableMock(spec=Deliverable)
        d2.full_id = "d2"
        d2.xml.is_xref = True
        target_elem = etree.Element("deliverable")
        d2.xml.final_target_node = target_elem

        mock_get_deliverables.return_value = [d1, d2]

        # Patch Deliverable instantiation inside the xref block
        with patch("docbuild.tasks.metadata.runner.Deliverable") as mock_deliverable:
            d_target = SortableMock(spec=Deliverable)
            d_target.full_id = "target"
            mock_deliverable.return_value = d_target

            result = _gather_build_tasks(empty_xml_root, [doctype])

        mock_get_deliverables.assert_called_once_with(empty_xml_root, doctype)

        # Results should be sorted by full_id ("d1", "target")
        assert len(result) == 2
        assert result[0].full_id == "d1"
        assert result[1].full_id == "target"


class TestExecuteBuildPipeline:
    """Tests for the _execute_build_pipeline phase."""

    @patch("docbuild.tasks.metadata.runner.update_repositories", new_callable=AsyncMock)
    @patch("docbuild.tasks.metadata.runner.process_deliverable", new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_success_with_deliverables(
        self, mock_process_deliverable: AsyncMock, mock_update_repositories: AsyncMock, tmp_path: Path
    ) -> None:
        """Verify pipeline processes deliverables cleanly."""
        d1 = SortableMock(spec=Deliverable)
        d1.full_id = "d1"
        d1.xml.git_remote.return_value = "https://github.com/foo/bar.git"
        d2 = SortableMock(spec=Deliverable)
        d2.full_id = "d2"
        d2.xml.git_remote.return_value = None

        mock_process_deliverable.side_effect = [(True, d1), (True, d2)]

        result = await _execute_build_pipeline(
            [d1, d2],
            repo_dir=tmp_path,
            tmp_repo_dir=tmp_path,
            meta_cache_dir=tmp_path,
            prebuilt_dir=tmp_path,
            dapsmetatmpl="daps_meta",
            daps_list_srcfiles_tmpl="daps_list",
            skip_repo_update=False,
            env_config_hash="hash",
            max_workers=2,
            exitfirst=False,
        )

        # Repositories should only be updated for deliverables with a git remote
        mock_update_repositories.assert_awaited_once_with([d1], tmp_path)
        assert mock_process_deliverable.await_count == 2
        assert result == []

    @patch("docbuild.tasks.metadata.runner.update_repositories", new_callable=AsyncMock)
    @patch("docbuild.tasks.metadata.runner.process_deliverable", new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_exitfirst_stops_on_first_failure(
        self, mock_process_deliverable: AsyncMock, mock_update_repositories: AsyncMock, tmp_path: Path
    ) -> None:
        """Verify exitfirst halts processing immediately on first failure."""
        d1 = SortableMock(spec=Deliverable)
        d2 = SortableMock(spec=Deliverable)

        # First fails, second succeeds
        mock_process_deliverable.side_effect = [(False, d1), (True, d2)]

        failed = await _execute_build_pipeline(
            [d1, d2],
            repo_dir=tmp_path,
            tmp_repo_dir=tmp_path,
            meta_cache_dir=tmp_path,
            prebuilt_dir=tmp_path,
            dapsmetatmpl="daps",
            daps_list_srcfiles_tmpl="daps_list",
            skip_repo_update=True,
            env_config_hash="hash",
            max_workers=1,  # Must be 1 to guarantee sequential execution order
            exitfirst=True,
        )

        assert failed == [d1]

    @patch("docbuild.tasks.metadata.runner.process_deliverable", new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_exception_in_process_deliverable_caught(
        self, mock_process_deliverable: AsyncMock, tmp_path: Path
    ) -> None:
        """Verify pipeline handles generic exceptions gracefully."""
        mock_d = SortableMock(spec=Deliverable)
        mock_d.full_id = "fail_mock"
        mock_process_deliverable.side_effect = Exception("Simulated DAPS failure")

        failed = await _execute_build_pipeline(
            [mock_d],
            repo_dir=tmp_path,
            tmp_repo_dir=tmp_path,
            meta_cache_dir=tmp_path,
            prebuilt_dir=tmp_path,
            dapsmetatmpl="daps",
            daps_list_srcfiles_tmpl="daps_list",
            skip_repo_update=True,
            env_config_hash="hash",
            max_workers=1,
            exitfirst=False,
        )

        assert failed == [mock_d]


class TestProcess:
    """Tests for the main process() orchestration function."""

    @pytest.fixture
    def runner_kwargs(self, tmp_path: Path) -> dict[str, object]:
        return {
            "main_portal_config": tmp_path / "portal.xml",
            "tmp_metadata_dir": tmp_path / "tmp" / "metadata",
            "repo_dir": tmp_path / "repos",
            "tmp_repo_dir": tmp_path / "tmp_repos",
            "meta_cache_dir": tmp_path / "cache" / "metadata",
            "json_cache_dir": tmp_path / "cache" / "json",
            "prebuilt_dir": tmp_path / "cache" / "prebuilt",
            "dapsmetatmpl": "daps",
            "daps_list_srcfiles_tmpl": "daps_list",
            "max_workers": 2,
            "doctypes": None,
        }

    @patch("docbuild.tasks.metadata.runner.store_productdocset_json")
    @patch("docbuild.tasks.metadata.runner._generate_homepage")
    @patch("docbuild.tasks.metadata.runner.parse_portal_config", new_callable=AsyncMock)
    @patch("docbuild.tasks.metadata.runner._gather_build_tasks")
    @patch("docbuild.tasks.metadata.runner._execute_build_pipeline", new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_empty_doctypes_uses_default(
        self,
        mock_execute: AsyncMock,
        mock_gather: Mock,
        mock_parse_portal_config: AsyncMock,
        mock_homepage: Mock,
        mock_store_json: Mock,
        runner_kwargs: dict[str, object],
    ) -> None:
        """Verify omitting doctypes uses wildcard default."""
        xml_string = """
        <docservconfig>
            <product id="sles">
              <name>SUSE Linux Enterprise Server</name>
              <docset id="sles.15-sp6" path="15-SP6"/>
            </product>
        </docservconfig>
        """
        mock_parse_portal_config.return_value = etree.ElementTree(
            etree.fromstring(xml_string)
        )
        mock_gather.return_value = []
        mock_execute.return_value = []

        result = await process(**runner_kwargs) # type: ignore

        assert result == 0
        # Ensure gather was called with the default broad doctype
        args, _ = mock_gather.call_args
        assert len(args[1]) == 1
        assert str(args[1][0]) == "*/*@supported/en-us"

    @patch("docbuild.tasks.metadata.runner.store_productdocset_json")
    @patch("docbuild.tasks.metadata.runner._generate_homepage")
    @patch("docbuild.tasks.metadata.runner.parse_portal_config", new_callable=AsyncMock)
    @patch("docbuild.tasks.metadata.runner._gather_build_tasks")
    @patch("docbuild.tasks.metadata.runner._execute_build_pipeline", new_callable=AsyncMock)
    @patch("docbuild.tasks.metadata.runner.console_err")
    @pytest.mark.asyncio
    async def test_failed_deliverables_returns_one(
        self,
        mock_console_err: Mock,
        mock_execute: AsyncMock,
        mock_gather: Mock,
        mock_parse_portal_config: AsyncMock,
        mock_homepage: Mock,
        mock_store_json: Mock,
        runner_kwargs: dict[str, object],
    ) -> None:
        """Verify failures map to exit code 1."""
        mock_parse_portal_config.return_value = etree.ElementTree(
            etree.Element("portal")
        )
        failed_d = Mock(spec=Deliverable)
        failed_d.full_id = "sles/15:test"

        mock_gather.return_value = [failed_d]
        mock_execute.return_value = [failed_d]

        result = await process(**runner_kwargs) # type: ignore

        assert result == 1
        assert mock_console_err.print.called

    @patch("docbuild.tasks.metadata.runner.store_productdocset_json")
    @patch("docbuild.tasks.metadata.runner._generate_homepage")
    @patch("docbuild.tasks.metadata.runner.parse_portal_config", new_callable=AsyncMock)
    @patch("docbuild.tasks.metadata.runner._gather_build_tasks")
    @patch("docbuild.tasks.metadata.runner._execute_build_pipeline", new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_provided_doctypes_skips_default(
        self,
        mock_execute: AsyncMock,
        mock_gather: Mock,
        mock_parse_portal_config: AsyncMock,
        mock_homepage: Mock,
        mock_store_json: Mock,
        runner_kwargs: dict[str, object],
    ) -> None:
        """Verify targeted execution isolates requested doctypes."""
        mock_parse_portal_config.return_value = etree.ElementTree(
            etree.Element("portal")
        )
        mock_gather.return_value = []
        mock_execute.return_value = []

        provided_doctype = Doctype.from_str("sles/15/en-us")
        runner_kwargs["doctypes"] = [provided_doctype]

        result = await process(**runner_kwargs) # type: ignore

        assert result == 0
        args, _ = mock_gather.call_args
        assert args[1] == [provided_doctype]
