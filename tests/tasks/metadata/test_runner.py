"""Unit tests for docbuild.tasks.metadata.runner."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from lxml import etree
import pytest

from docbuild.cli.context import DocBuildContext
from docbuild.constants import DEFAULT_DELIVERABLES
from docbuild.models.deliverable import Deliverable
from docbuild.models.doctype import Doctype
from docbuild.models.repo import Repo
import docbuild.tasks.metadata.runner as runner_pkg
from docbuild.tasks.metadata.runner import (
    get_deliverable_worker_limit,
    process,
    process_doctype,
    run_tasks_collect_all,
    run_tasks_fail_fast,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_envconfig(tmp_path: Path) -> Mock:
    """Provide a mock EnvConfig with the paths and build config needed by runner."""
    mock_paths = Mock()
    mock_paths.repo_dir = tmp_path / "repos"
    mock_paths.meta_cache_dir = tmp_path / "cache" / "metadata"
    mock_paths.tmp_repo_dir = tmp_path / "tmp_repos"

    mock_build = Mock()
    mock_build.daps.meta = "daps-command-template"

    env = Mock()
    env.paths = mock_paths
    env.build = mock_build
    return env


@pytest.fixture
def mock_context(mock_envconfig: Mock) -> DocBuildContext:
    """DocBuildContext backed by mock_envconfig."""
    ctx = Mock(spec=DocBuildContext)
    ctx.envconfig = mock_envconfig
    ctx.appconfig = Mock(max_workers=8)
    return ctx


@pytest.fixture
def mock_context_with_config_dir(tmp_path: Path, mock_envconfig: Mock) -> DocBuildContext:
    """DocBuildContext with a real config_dir and tmp_metadata_dir on disk."""
    config_dir = tmp_path / "config"
    tmp_metadata_dir = tmp_path / "tmp" / "metadata"

    config_dir.mkdir()
    tmp_metadata_dir.mkdir(parents=True)
    (config_dir / "dummy.xml").write_text("<docservconfig/>")

    mock_envconfig.paths.config_dir = config_dir
    mock_envconfig.paths.main_portal_config = config_dir / "dummy.xml"
    mock_envconfig.paths.meta_cache_dir.mkdir(parents=True, exist_ok=True)

    mock_tmp = Mock()
    mock_tmp.tmp_metadata_dir = tmp_metadata_dir
    mock_envconfig.paths.tmp = mock_tmp

    ctx = Mock(spec=DocBuildContext)
    ctx.envconfig = mock_envconfig
    ctx.appconfig = Mock(max_workers=8)
    return ctx


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
        mock_context: DocBuildContext,
    ):
        """No failures are returned when all deliverables succeed."""
        doctype = Doctype.from_str("sles/15/en-us")
        mock_d = Mock(spec=Deliverable, git=Mock(spec=Repo, url="gh://SUSE/doc-test"))
        mock_get_deliverables.return_value = [mock_d, mock_d]
        mock_process_deliverable.return_value = (True, mock_d)

        result = await process_doctype(empty_xml_root, mock_context, doctype, exitfirst=False)

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
        mock_context: DocBuildContext,
    ):
        """When no deliverables are found, process_deliverable is never called."""
        doctype = Doctype.from_str("sles/15/en-us")
        mock_get_deliverables.return_value = []

        result = await process_doctype(empty_xml_root, mock_context, doctype)

        assert result == []
        mock_process_deliverable.assert_not_called()

    @patch.object(runner_pkg, "get_deliverable_from_doctype")
    async def test_missing_repo_dir_raises(
        self,
        mock_get_deliverables: Mock,
        empty_xml_root: etree._ElementTree,
        mock_envconfig: Mock,
    ):
        """AttributeError is raised when repo_dir is missing from config."""
        doctype = Doctype.from_str("sles/15/en-us")
        mock_get_deliverables.return_value = [Mock(spec=Deliverable)]

        ctx = Mock(spec=DocBuildContext)
        del mock_envconfig.paths.repo_dir
        ctx.envconfig = mock_envconfig

        with pytest.raises(AttributeError):
            await process_doctype(empty_xml_root, ctx, doctype)

    @patch.object(runner_pkg, "process_deliverable", new_callable=AsyncMock)
    @patch.object(runner_pkg, "get_deliverable_from_doctype")
    @patch.object(runner_pkg, "update_repositories", new_callable=AsyncMock)
    async def test_exitfirst_stops_on_first_failure(
        self,
        mock_update_repositories: AsyncMock,
        mock_get_deliverables: Mock,
        mock_process_deliverable: AsyncMock,
        empty_xml_root: etree._ElementTree,
        mock_context: DocBuildContext,
    ):
        """With exitfirst=True, only the first failing deliverable is reported."""
        doctype = Doctype.from_str("sles/15/en-us")
        d1 = Mock(spec=Deliverable, full_id="sles/15/en-us:DC-ONE")
        d2 = Mock(spec=Deliverable, full_id="sles/15/en-us:DC-TWO")
        mock_get_deliverables.return_value = [d1, d2]
        mock_process_deliverable.side_effect = [(False, d1), (True, d2)]

        failed = await process_doctype(empty_xml_root, mock_context, doctype, exitfirst=True)

        assert failed == [d1]

    @patch.object(runner_pkg, "get_deliverable_from_doctype")
    async def test_max_workers_limits_in_flight_deliverables(
        self,
        mock_get_deliverables: Mock,
        empty_xml_root: etree._ElementTree,
        mock_context: DocBuildContext,
    ):
        """Deliverable processing respects the configured max_workers limit."""
        doctype = Doctype.from_str("sles/15/en-us")
        deliverables = [
            Mock(spec=Deliverable, full_id=f"sles/15/en-us:DC-{index}")
            for index in range(3)
        ]
        mock_get_deliverables.return_value = deliverables
        mock_context.appconfig.max_workers = 1

        active = 0
        max_active = 0
        lock = asyncio.Lock()

        async def fake_process_deliverable(*args, **kwargs):
            nonlocal active, max_active
            deliverable = kwargs["deliverable"] if "deliverable" in kwargs else args[1]
            async with lock:
                active += 1
                max_active = max(max_active, active)
            await asyncio.sleep(0)
            async with lock:
                active -= 1
            return True, deliverable

        with patch.object(runner_pkg, "process_deliverable", side_effect=fake_process_deliverable):
            result = await process_doctype(
                empty_xml_root,
                mock_context,
                doctype,
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
        mock_context_with_config_dir: DocBuildContext,
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
            result = await process(mock_context_with_config_dir, doctypes=tuple())

        assert result == 0
        mock_parse_portal_config.assert_awaited_once()
        mock_store_json.assert_called_once()
        default_doctype = Doctype.from_str(DEFAULT_DELIVERABLES)
        mock_process_doctype.assert_awaited_once_with(
            mock_parse_portal_config.return_value,
            mock_context_with_config_dir,
            default_doctype,
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
        mock_context_with_config_dir: DocBuildContext,
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
            result = await process(mock_context_with_config_dir, doctypes=tuple())

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
        mock_context_with_config_dir: DocBuildContext,
    ):
        """process() with provided doctypes skips the default fallback (line 201->204 branch)."""
        mock_parse_portal_config.return_value = etree.ElementTree(
            etree.fromstring("<docservconfig/>")
        )
        mock_process_doctype.return_value = []
        provided_doctype = Doctype.from_str("sles/15/en-us")

        with patch.object(runner_pkg, "stdout"):
            result = await process(
                mock_context_with_config_dir,
                doctypes=[provided_doctype],
            )

        assert result == 0
        mock_process_doctype.assert_awaited_once_with(
            mock_parse_portal_config.return_value,
            mock_context_with_config_dir,
            provided_doctype,
            exitfirst=False,
            skip_repo_update=False,
        )


# ---------------------------------------------------------------------------
# get_deliverable_worker_limit tests
# ---------------------------------------------------------------------------

def test_get_deliverable_worker_limit_zero_returns_one():
    """deliverable_count <= 0 always returns 1 (line 37 branch)."""
    ctx = Mock(spec=DocBuildContext)
    assert get_deliverable_worker_limit(ctx, 0) == 1
    assert get_deliverable_worker_limit(ctx, -5) == 1


def test_get_deliverable_worker_limit_no_appconfig_returns_count():
    """When appconfig is None, deliverable_count is returned unchanged (line 41 branch)."""
    ctx = Mock(spec=DocBuildContext)
    ctx.appconfig = None
    assert get_deliverable_worker_limit(ctx, 7) == 7


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
