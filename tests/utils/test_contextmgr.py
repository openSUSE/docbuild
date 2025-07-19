import math
import asyncio
from pathlib import Path
import time
from unittest.mock import patch

import pytest

import docbuild.utils.contextmgr as contextmgr
from docbuild.utils.contextmgr import PersistentOnErrorTemporaryDirectory, make_timer


def test_timer_has_correct_attributes():
    timer_name = 'test-timer'
    sleep_duration = 0.1
    time_func = make_timer(timer_name)

    with time_func() as timer_data:
        time.sleep(sleep_duration)

    for key in ('name', 'start', 'end', 'elapsed'):
        assert hasattr(timer_data, key), f"Expected key '{key}' not found in timer_data"


def test_timer_as_context_manager_measures_time():
    timer_name = 'test-timer'
    sleep_duration = 0.1
    timer = make_timer(timer_name)

    with timer() as timer_data:
        time.sleep(sleep_duration)

    elapsed = timer_data.elapsed
    assert isinstance(elapsed, float)
    assert elapsed == pytest.approx(sleep_duration, abs=0.05)


def test_timer_factory_creates_independent_timers():
    timer_name1 = 'test-timer-1'
    timer_name2 = 'test-timer-2'
    sleep_duration = 0.1

    timer1 = make_timer(timer_name1)
    timer2 = make_timer(timer_name2)

    with timer1() as timer_data1:
        time.sleep(sleep_duration)

    with timer2() as timer_data2:
        time.sleep(sleep_duration * 2)

    assert timer_data1.name == timer_name1
    assert timer_data2.name == timer_name2
    assert timer_data1.elapsed != timer_data2.elapsed
    assert isinstance(timer_data1.elapsed, float)
    assert isinstance(timer_data2.elapsed, float)
    assert timer_data1.elapsed == pytest.approx(sleep_duration, abs=0.01)
    assert timer_data2.elapsed == pytest.approx(sleep_duration * 2, abs=0.01)


def test_timer_for_nan_as_default():
    timer_name = 'test-timer'
    timer = make_timer(timer_name)
    sleep_duration = 0.1

    with timer() as timer_data:
        time.sleep(sleep_duration)
        assert timer_data.start > 0
        assert math.isnan(timer_data.end)
        assert math.isnan(timer_data.elapsed)


# ----
@pytest.fixture
def fake_temp_path() -> str:
    return '/mock/temp/dir'


def test_temp_dir_deleted_on_success(fake_temp_path: str) -> None:
    """Ensure the directory is deleted if no exception occurs."""
    with (
        patch.object(
            contextmgr.tempfile,
            'mkdtemp',
            return_value=fake_temp_path,
        ),
        patch.object(contextmgr.shutil, 'rmtree') as mock_rmtree,
    ):
        with PersistentOnErrorTemporaryDirectory() as temp_path:
            assert temp_path == Path(fake_temp_path)

        mock_rmtree.assert_called_once_with(fake_temp_path)


def test_temp_dir_preserved_on_exception(fake_temp_path: str) -> None:
    """Ensure the directory is preserved if an exception occurs."""
    with (
        patch.object(contextmgr.tempfile, 'mkdtemp', return_value=fake_temp_path),
        patch.object(contextmgr.shutil, 'rmtree') as mock_rmtree,
    ):
        with pytest.raises(RuntimeError):
            with PersistentOnErrorTemporaryDirectory() as temp_path:
                assert temp_path == Path(fake_temp_path)
                raise RuntimeError('Simulated failure')

        mock_rmtree.assert_not_called()


def test_temp_dir_deletion_failure_is_logged(fake_temp_path: str) -> None:
    """Ensure that an OSError during directory deletion is logged."""
    mock_error = OSError('Permission denied')

    with (
        patch.object(contextmgr.tempfile, 'mkdtemp', return_value=fake_temp_path),
        patch.object(
            contextmgr.shutil, 'rmtree', side_effect=mock_error
        ) as mock_rmtree,
        patch.object(contextmgr.log, 'exception') as mock_log_exception,
    ):
        # The __exit__ method should catch the OSError and not re-raise it.
        with PersistentOnErrorTemporaryDirectory() as temp_path:
            assert temp_path == Path(fake_temp_path)

        # Verify that rmtree was called, which triggered the error
        mock_rmtree.assert_called_once_with(fake_temp_path)
        # Verify that the exception was logged with the correct message.
        mock_log_exception.assert_called_once_with(
            'Failed to delete temp dir %s: %s', fake_temp_path, mock_error
        )


async def test_async_temp_dir_deleted_on_success(fake_temp_path: str) -> None:
    """Ensure the directory is deleted if no exception occurs in an async context."""
    with (
        patch.object(contextmgr.tempfile, 'mkdtemp', return_value=fake_temp_path),
        patch.object(contextmgr.shutil, 'rmtree') as mock_rmtree,
    ):
        async with PersistentOnErrorTemporaryDirectory() as temp_path:
            assert temp_path == Path(fake_temp_path)

        await asyncio.sleep(0)  # Allow event loop to run the thread
        mock_rmtree.assert_called_once_with(fake_temp_path)


async def test_async_temp_dir_preserved_on_exception(fake_temp_path: str) -> None:
    """Ensure the directory is preserved if an exception occurs in an async context."""
    with (
        patch.object(contextmgr.tempfile, 'mkdtemp', return_value=fake_temp_path),
        patch.object(contextmgr.shutil, 'rmtree') as mock_rmtree,
    ):
        with pytest.raises(RuntimeError):
            async with PersistentOnErrorTemporaryDirectory() as temp_path:
                assert temp_path == Path(fake_temp_path)
                raise RuntimeError('Simulated failure')

        await asyncio.sleep(0)
        mock_rmtree.assert_not_called()


async def test_async_temp_dir_deletion_failure_is_logged(fake_temp_path: str) -> None:
    """Ensure that an OSError during async directory deletion is logged."""
    mock_error = OSError('Permission denied')
    with (
        patch.object(contextmgr.tempfile, 'mkdtemp', return_value=fake_temp_path),
        patch.object(
            contextmgr.shutil, 'rmtree', side_effect=mock_error
        ) as mock_rmtree,
        patch.object(contextmgr.log, 'exception') as mock_log_exception,
    ):
        async with PersistentOnErrorTemporaryDirectory() as temp_path:
            assert temp_path == Path(fake_temp_path)

        await asyncio.sleep(0)
        mock_rmtree.assert_called_once_with(fake_temp_path)
        mock_log_exception.assert_called_once_with(
            'Failed to delete temp dir %s: %s', fake_temp_path, mock_error
        )
