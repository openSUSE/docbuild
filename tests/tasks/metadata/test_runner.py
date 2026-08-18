"""Unit tests for docbuild.tasks.metadata.runner."""

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

from lxml import etree  # type: ignore
import pytest

from docbuild.constants import DEFAULT_DELIVERABLES
from docbuild.models.deliverable import Deliverable
from docbuild.models.doctype import Doctype
from docbuild.models.repo import Repo
import docbuild.tasks.metadata.runner as runner_pkg
from docbuild.tasks.metadata.runner import (
    process,
    process_doctype,
)


class SortableMock(Mock):
    """A Mock that supports sorting by the full_id attribute."""

    def __lt__(self, other: object) -> bool:
        return str(getattr(self, "full_id", "")) < str(getattr(other, "full_id", ""))


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def runner_kwargs(tmp_path: Path) -> dict[str, Any]:
    """Provide explicit arguments required by process()."""
    return {
        "main_portal_config": tmp_path / "config" / "portal.xml",
        "tmp_metadata_dir": tmp_path / "tmp" / "metadata",
        "repo_dir": tmp_path / "repos",
        "tmp_repo_dir": tmp_path / "tmp_repos",
        "meta_cache_dir": tmp_path / "cache" / "metadata",
        "json_cache_dir": tmp_path / "cache" / "json",
        "dapsmetatmpl": "daps-command-template",
        "max_workers": 8,
    }


@pytest.fixture
def empty_xml_root() -> etree._ElementTree:
    """Return a minimal empty docservconfig ElementTree."""
    return etree.ElementTree(etree.fromstring("<docservconfig/>"))


# ---------------------------------------------------------------------------
# process_doctype tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestProcessDoctype:
    """Tests for process_doctype."""

    @patch.object(runner_pkg, "process_deliverable", new_callable=AsyncMock)
    @patch.object(runner_pkg, "get_deliverable_from_doctype")
    async def test_success_with_deliverables(
        self,
        mock_get_deliverables: Mock,
        mock_process_deliverable: AsyncMock,
        empty_xml_root: etree._ElementTree,
        tmp_path: Path,
    ) -> None:
        """No failures are returned when all deliverables succeed."""
        doctype = Doctype.from_str("sles/15/en-us")

        # Use SortableMock with distinct IDs so they can be sorted safely
        d1 = SortableMock(
            spec=Deliverable,
            full_id="sles/15/en-us:DC-A",
            git=Mock(spec=Repo, url="gh://SUSE/doc-test")
        )
        d2 = SortableMock(
            spec=Deliverable,
            full_id="sles/15/en-us:DC-B",
            git=Mock(spec=Repo, url="gh://SUSE/doc-test")
        )

        # Feed them in reverse order to ensure sorting works without crashing
        mock_get_deliverables.return_value = [d2, d1]
        mock_process_deliverable.return_value = (True, d1)

        result = await process_doctype(
            root=empty_xml_root,
            doctype=doctype,
            repo_dir=tmp_path / "repos",
            tmp_repo_dir=tmp_path / "tmp_repos",
            meta_cache_dir=tmp_path / "cache" / "metadata",
            dapsmetatmpl="daps-template",
            max_workers=8,
            exitfirst=False,
            skip_repo_update=True,
        )

        assert result == []
        mock_get_deliverables.assert_called_once_with(empty_xml_root, doctype)
        assert mock_process_deliverable.call_count == 2

    @patch.object(runner_pkg, "process_deliverable", new_callable=AsyncMock)
    @patch.object(runner_pkg, "get_deliverable_from_doctype")
    async def test_no_deliverables_found(
        self,
        mock_get_deliverables: Mock,
        mock_process_deliverable: AsyncMock,
        empty_xml_root: etree._ElementTree,
        tmp_path: Path,
    ) -> None:
        """When no deliverables are found, process_deliverable is never called."""
        doctype = Doctype.from_str("sles/15/en-us")
        mock_get_deliverables.return_value = []

        result = await process_doctype(
            root=empty_xml_root,
            doctype=doctype,
            repo_dir=tmp_path / "repos",
            tmp_repo_dir=tmp_path / "tmp_repos",
            meta_cache_dir=tmp_path / "cache" / "metadata",
            dapsmetatmpl="daps-template",
            max_workers=8,
            exitfirst=False,
            skip_repo_update=True,
        )

        assert result == []
        mock_process_deliverable.assert_not_called()

    @patch.object(runner_pkg, "process_deliverable", new_callable=AsyncMock)
    @patch.object(runner_pkg, "get_deliverable_from_doctype")
    @patch.object(runner_pkg, "update_repositories", new_callable=AsyncMock)
    async def test_exitfirst_stops_on_first_failure(
        self,
        mock_update_repositories: AsyncMock,
        mock_get_deliverables: Mock,
        mock_process_deliverable: AsyncMock,
        empty_xml_root: etree._ElementTree,
        tmp_path: Path,
    ) -> None:
        """With exitfirst=True, only the first failing deliverable is reported."""
        doctype = Doctype.from_str("sles/15/en-us")
        d1 = SortableMock(spec=Deliverable, full_id="sles/15/en-us:DC-ONE")
        d2 = SortableMock(spec=Deliverable, full_id="sles/15/en-us:DC-TWO")
        mock_get_deliverables.return_value = [d1, d2]

        # In a real aiostream pipeline, breaking the loop cancels the rest.
        # We test that `exitfirst=True` correctly breaks the stream and only returns `d1`.
        mock_process_deliverable.side_effect = [(False, d1), (True, d2)]

        failed = await process_doctype(
            root=empty_xml_root,
            doctype=doctype,
            repo_dir=tmp_path / "repos",
            tmp_repo_dir=tmp_path / "tmp_repos",
            meta_cache_dir=tmp_path / "cache" / "metadata",
            dapsmetatmpl="daps-template",
            max_workers=1,  # Force sequential to guarantee order in test
            exitfirst=True,
            skip_repo_update=True,
        )

        assert failed == [d1]

    @patch.object(runner_pkg, "process_deliverable", new_callable=AsyncMock)
    @patch.object(runner_pkg, "get_deliverable_from_doctype")
    async def test_exception_in_process_deliverable_caught(
        self,
        mock_get_deliverables: Mock,
        mock_process_deliverable: AsyncMock,
        empty_xml_root: etree._ElementTree,
        tmp_path: Path,
    ) -> None:
        """Exceptions in the pipeline wrapper are caught and treated as failures."""
        doctype = Doctype.from_str("sles/15/en-us")
        mock_d = SortableMock(spec=Deliverable, full_id="test:DC-ERROR")
        mock_get_deliverables.return_value = [mock_d]
        mock_process_deliverable.side_effect = RuntimeError("Simulated failure")

        failed = await process_doctype(
            root=empty_xml_root,
            doctype=doctype,
            repo_dir=tmp_path / "repos",
            tmp_repo_dir=tmp_path / "tmp_repos",
            meta_cache_dir=tmp_path / "cache" / "metadata",
            dapsmetatmpl="daps-template",
            max_workers=8,
            exitfirst=False,
            skip_repo_update=True,
        )

        assert failed == [mock_d]


# ---------------------------------------------------------------------------
# process tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestProcess:
    """Tests for the top-level process() function."""

    @patch.object(runner_pkg, "store_productdocset_json", new_callable=Mock)
    @patch.object(runner_pkg, "parse_portal_config", new_callable=AsyncMock)
    @patch.object(runner_pkg, "process_doctype", new_callable=AsyncMock)
    async def test_empty_doctypes_uses_default(
        self,
        mock_process_doctype: AsyncMock,
        mock_parse_portal_config: AsyncMock,
        mock_store_json: Mock,
        runner_kwargs: dict[str, Any],
    ) -> None:
        """When no doctypes are given, the DEFAULT_DELIVERABLES doctype is used."""
        xml_string = """
        <docservconfig>
            <product id="sles">
              <name>SUSE Linux Enterprise Server</name>
              <acronym>SLES</acronym>
              <docset id="sles.15-sp6" path="15-SP6"/>
            </product>
        </docservconfig>
        """
        mock_parse_portal_config.return_value = etree.ElementTree(
            etree.fromstring(xml_string)
        )
        mock_process_doctype.return_value = []

        with patch.object(runner_pkg, "stdout"):
            result = await process(**runner_kwargs, doctypes=tuple())

        assert result == 0
        mock_parse_portal_config.assert_awaited_once()
        mock_store_json.assert_called_once()
        default_doctype = Doctype.from_str(DEFAULT_DELIVERABLES)

        mock_process_doctype.assert_awaited_once_with(
            mock_parse_portal_config.return_value,
            default_doctype,
            runner_kwargs["repo_dir"],
            runner_kwargs["tmp_repo_dir"],
            runner_kwargs["meta_cache_dir"],
            runner_kwargs["dapsmetatmpl"],
            runner_kwargs["max_workers"],
            exitfirst=False,
            skip_repo_update=False,
        )

    @patch.object(runner_pkg, "store_productdocset_json", new_callable=Mock)
    @patch.object(runner_pkg, "parse_portal_config", new_callable=AsyncMock)
    @patch.object(runner_pkg, "process_doctype", new_callable=AsyncMock)
    async def test_failed_deliverables_returns_one(
        self,
        mock_process_doctype: AsyncMock,
        mock_parse_portal_config: AsyncMock,
        mock_store_json: Mock,
        runner_kwargs: dict[str, Any],
    ) -> None:
        """process() returns 1 and prints to console_err when deliverables fail."""
        xml_string = """
        <docservconfig>
            <product id="sles">
              <name>SUSE Linux Enterprise Server</name>
              <acronym>SLES</acronym>
              <docset id="sles.15-sp6" path="15-SP6"/>
            </product>
        </docservconfig>
        """
        mock_parse_portal_config.return_value = etree.ElementTree(
            etree.fromstring(xml_string)
        )
        failed_d = Mock(spec=Deliverable, full_id="sles/15-sp6/en-us:DC-FAIL")
        mock_process_doctype.return_value = [failed_d]

        with patch.object(runner_pkg, "console_err") as mock_console_err:
            result = await process(**runner_kwargs, doctypes=tuple())

        assert result == 1
        assert mock_console_err.print.called

    @patch.object(runner_pkg, "store_productdocset_json", new_callable=Mock)
    @patch.object(runner_pkg, "parse_portal_config", new_callable=AsyncMock)
    @patch.object(runner_pkg, "process_doctype", new_callable=AsyncMock)
    async def test_provided_doctypes_skips_default(
        self,
        mock_process_doctype: AsyncMock,
        mock_parse_portal_config: AsyncMock,
        mock_store_json: Mock,
        runner_kwargs: dict[str, Any],
    ) -> None:
        """process() with provided doctypes skips the default fallback."""
        mock_parse_portal_config.return_value = etree.ElementTree(
            etree.fromstring("<docservconfig/>")
        )
        mock_process_doctype.return_value = []
        provided_doctype = Doctype.from_str("sles/15/en-us")

        with patch.object(runner_pkg, "stdout"):
            result = await process(**runner_kwargs, doctypes=[provided_doctype])

        assert result == 0
        mock_process_doctype.assert_awaited_once_with(
            mock_parse_portal_config.return_value,
            provided_doctype,
            runner_kwargs["repo_dir"],
            runner_kwargs["tmp_repo_dir"],
            runner_kwargs["meta_cache_dir"],
            runner_kwargs["dapsmetatmpl"],
            runner_kwargs["max_workers"],
            exitfirst=False,
            skip_repo_update=False,
        )
