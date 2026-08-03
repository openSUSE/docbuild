"""Unit tests for docbuild.tasks.metadata.runner."""

import asyncio
from pathlib import Path
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
    run_tasks_collect_all,
    run_tasks_fail_fast,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def runner_kwargs(tmp_path: Path) -> dict:
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
    ):
        """No failures are returned when all deliverables succeed."""
        doctype = Doctype.from_str("sles/15/en-us")
        mock_d = Mock(spec=Deliverable, git=Mock(spec=Repo, url="gh://SUSE/doc-test"))
        mock_get_deliverables.return_value = [mock_d, mock_d]
        mock_process_deliverable.return_value = (True, mock_d)

        result = await process_doctype(
            root=empty_xml_root,
            doctype=doctype,
            repo_dir=tmp_path / "repos",
            tmp_repo_dir=tmp_path / "tmp_repos",
            meta_cache_dir=tmp_path / "cache" / "metadata",
            dapsmetatmpl="daps-template",
            max_workers=8,
            exitfirst=False,
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
    ):
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
    ):
        """With exitfirst=True, only the first failing deliverable is reported."""
        doctype = Doctype.from_str("sles/15/en-us")
        d1 = Mock(spec=Deliverable, full_id="sles/15/en-us:DC-ONE")
        d2 = Mock(spec=Deliverable, full_id="sles/15/en-us:DC-TWO")
        mock_get_deliverables.return_value = [d1, d2]
        mock_process_deliverable.side_effect = [(False, d1), (True, d2)]

        failed = await process_doctype(
            root=empty_xml_root,
            doctype=doctype,
            repo_dir=tmp_path / "repos",
            tmp_repo_dir=tmp_path / "tmp_repos",
            meta_cache_dir=tmp_path / "cache" / "metadata",
            dapsmetatmpl="daps-template",
            max_workers=8,
            exitfirst=True,
        )

        assert failed == [d1]

    @patch.object(runner_pkg, "get_deliverable_from_doctype")
    async def test_max_workers_limits_in_flight_deliverables(
        self,
        mock_get_deliverables: Mock,
        empty_xml_root: etree._ElementTree,
        tmp_path: Path,
    ):
        """Deliverable processing respects the configured max_workers limit."""
        doctype = Doctype.from_str("sles/15/en-us")
        deliverables = [
            Mock(spec=Deliverable, full_id=f"sles/15/en-us:DC-{index}")
            for index in range(3)
        ]
        mock_get_deliverables.return_value = deliverables

        active = 0
        max_active = 0
        lock = asyncio.Lock()

        async def fake_process_deliverable(*args, **kwargs):
            nonlocal active, max_active
            deliverable = kwargs["deliverable"] if "deliverable" in kwargs else args[0]
            async with lock:
                active += 1
                max_active = max(max_active, active)
            await asyncio.sleep(0)
            async with lock:
                active -= 1
            return True, deliverable

        with patch.object(runner_pkg, "process_deliverable", side_effect=fake_process_deliverable):
            result = await process_doctype(
                root=empty_xml_root,
                doctype=doctype,
                repo_dir=tmp_path / "repos",
                tmp_repo_dir=tmp_path / "tmp_repos",
                meta_cache_dir=tmp_path / "cache" / "metadata",
                dapsmetatmpl="daps-template",
                max_workers=1,
                skip_repo_update=True,
            )

        assert result == []
        assert max_active == 1


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
        runner_kwargs: dict,
    ):
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
        runner_kwargs: dict,
    ):
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
        runner_kwargs: dict,
    ):
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


# ---------------------------------------------------------------------------
# run_tasks_fail_fast tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_tasks_fail_fast_empty_list():
    """Empty task list exits immediately and returns [] (line 53->68 branch)."""
    result = await run_tasks_fail_fast([])
    assert result == []


@pytest.mark.asyncio
async def test_run_tasks_fail_fast_all_succeed():
    """All tasks succeed in fail-fast mode; loop iterates without breaking (line 56->53 branch)."""
    d1 = Mock(spec=Deliverable, full_id="test:DC-ONE")
    d2 = Mock(spec=Deliverable, full_id="test:DC-TWO")

    async def succeed(d: Deliverable) -> tuple[bool, Deliverable]:
        return True, d

    tasks = [asyncio.create_task(succeed(d1)), asyncio.create_task(succeed(d2))]
    result = await run_tasks_fail_fast(tasks)
    assert result == []


@pytest.mark.asyncio
async def test_run_tasks_fail_fast_task_raises(caplog: pytest.LogCaptureFixture):
    """An unexpected exception in a task is caught and logged (lines 60, 62-67)."""
    import logging

    async def raising() -> None:
        raise RuntimeError("unexpected boom")

    tasks = [asyncio.create_task(raising())]
    with caplog.at_level(logging.ERROR):
        result = await run_tasks_fail_fast(tasks)

    assert result == []
    assert any("Task failed unexpectedly" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_run_tasks_fail_fast_cancels_pending_on_failure():
    """Pending tasks are cancelled when a task returns failure (line 60 branch)."""
    d = Mock(spec=Deliverable, full_id="test:FAIL")
    gate = asyncio.Event()

    async def slow() -> tuple[bool, Deliverable]:
        await gate.wait()   # blocks indefinitely; cancelled from outside
        return True, d      # pragma: no cover

    async def fail() -> tuple[bool, Deliverable]:
        return False, d

    task_fail = asyncio.create_task(fail())
    task_slow = asyncio.create_task(slow())

    result = await run_tasks_fail_fast([task_fail, task_slow])
    await asyncio.sleep(0)  # let cancellation propagate

    assert result == [d]
    assert task_slow.cancelled()


@pytest.mark.asyncio
async def test_run_tasks_fail_fast_cancels_pending_on_exception():
    """Pending tasks are cancelled when a task raises (line 66 branch)."""
    gate = asyncio.Event()

    async def slow() -> None:
        await gate.wait()   # blocks indefinitely; cancelled from outside  # pragma: no cover

    async def raising() -> None:
        raise RuntimeError("boom")

    task_raise = asyncio.create_task(raising())
    task_slow = asyncio.create_task(slow())

    result = await run_tasks_fail_fast([task_raise, task_slow])
    await asyncio.sleep(0)

    assert result == []
    assert task_slow.cancelled()


# ---------------------------------------------------------------------------
# run_tasks_collect_all tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_tasks_collect_all_exception_result(caplog: pytest.LogCaptureFixture):
    """A task that raises is logged and its deliverable collected as failed (lines 86-89)."""
    import logging

    d1 = Mock(spec=Deliverable, full_id="test:DC-RAISE")

    async def raising() -> None:
        raise ValueError("task error")

    tasks = [asyncio.create_task(raising())]
    with caplog.at_level(logging.ERROR):
        result = await run_tasks_collect_all(tasks, [d1])

    assert result == [d1]
    assert any("Error in task" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_run_tasks_collect_all_failed_tuple():
    """A task returning (False, deliverable) adds it to failed (line 86 branch)."""
    d_fail = Mock(spec=Deliverable, full_id="test:DC-FAIL")

    async def fail_task() -> tuple[bool, Deliverable]:
        return False, d_fail

    tasks = [asyncio.create_task(fail_task())]
    result = await run_tasks_collect_all(tasks, [d_fail])
    assert result == [d_fail]


@pytest.mark.asyncio
async def test_run_tasks_collect_all_exception_then_success():
    """Loop continues after an exception result, processing remaining items (line 87->82 branch)."""
    d_err = Mock(spec=Deliverable, full_id="test:DC-ERR")
    d_ok = Mock(spec=Deliverable, full_id="test:DC-OK")

    async def raising() -> None:
        raise ValueError("error")

    async def succeed() -> tuple[bool, Deliverable]:
        return True, d_ok

    tasks = [asyncio.create_task(raising()), asyncio.create_task(succeed())]
    result = await run_tasks_collect_all(tasks, [d_err, d_ok])
    assert result == [d_err]
