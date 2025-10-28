"""Tests for the PidFileLock utility."""

import errno
import logging
import os
import shutil
from pathlib import Path, PosixPath
from unittest.mock import patch, MagicMock
from pathlib import PosixPath

import pytest

from docbuild.utils.pidlock import PidFileLock

log = logging.getLogger(__name__)

# --- Helper Fixtures and Mocks ---


@pytest.fixture
def mock_pid_running(monkeypatch):
    """
    Mocks os.kill to simulate a running process (PID exists).
    os.kill(pid, 0) succeeds if the process exists.
    """

    def mock_kill(pid, sig):
        if pid == 12345:  # Mock PID of a running process used in the test
            return
        # For any other PID, assume dead (simulating ESRCH)
        raise OSError(errno.ESRCH, 'No such process')

    monkeypatch.setattr(os, 'kill', mock_kill)


@pytest.fixture
def mock_pid_dead(monkeypatch):
    """
    Mocks os.kill to simulate a dead process (PID does not exist).
    """

    def mock_kill(pid, sig):
        # Always raise ESRCH (No such process) for any checked PID
        raise OSError(errno.ESRCH, 'No such process')

    monkeypatch.setattr(os, 'kill', mock_kill)


@pytest.fixture
def lock_setup(tmp_path: Path) -> tuple[Path, Path]:
    """Provides a resource path and the temporary lock directory."""
    resource_path = tmp_path / 'env.production.toml'
    resource_path.touch()  # The resource path must exist
    lock_dir = tmp_path / 'locks'
    return resource_path, lock_dir


# --- Test Cases ---


def test_acquire_and_release_success(lock_setup):
    """Test successful lock acquisition and release using a context manager."""
    resource_path, lock_dir = lock_setup

    current_pid = os.getpid()

    lock = PidFileLock(resource_path, lock_dir)
    assert not lock.lock_path.exists()

    # Acquire lock via context manager
    with lock:
        assert lock.lock is True
        assert lock.lock_path.exists()

        # Verify content is the current PID
        assert lock.lock_path.read_text().strip() == str(current_pid)

    # Verify lock file is released (deleted)
    assert lock.lock is False
    assert not lock.lock_path.exists()


def test_stale_lock_is_cleaned_up(lock_setup, mock_pid_dead):
    """
    Test that a stale (dead process) lock is removed and a new one is acquired.
    Uses context manager to ensure explicit release and avoid atexit race condition.
    """
    resource_path, lock_dir = lock_setup
    lock_dir.mkdir()

    # 1. Manually create a stale lock file with a fake PID
    stale_pid = 9999
    lock_path = PidFileLock(resource_path, lock_dir).lock_path
    lock_path.write_text(str(stale_pid))

    # 2. Attempt to acquire the lock using a context manager to ensure release
    lock = PidFileLock(resource_path, lock_dir)
    with lock:
        # 3. Verify the stale lock was removed and a new one was acquired
        assert lock.lock is True
        assert lock.lock_path.exists()
        assert lock.lock_path.read_text().strip() == str(os.getpid())
        log.info('Stale lock successfully cleaned and re-acquired.')

    # 4. Verify the lock is released after the context manager exits
    assert lock.lock is False
    assert not lock.lock_path.exists()


def test_stale_lock_handles_race_and_invalid_pid(
    lock_setup, mock_pid_dead, monkeypatch, caplog, capsys
):
    """
    Test two specific failure paths during stale lock cleanup:
    1. Lock file contains an invalid PID (ValueError).
    2. Lock file is removed by another process during cleanup (FileNotFoundError race).
    """
    resource_path, lock_dir = lock_setup
    lock_dir.mkdir()

    # --- Scenario 1: Invalid PID (ValueError) ---

    # 1. Create a lock file with invalid content
    lock_path = PidFileLock(resource_path, lock_dir).lock_path
    lock_path.write_text('not_a_pid_123')

    lock = PidFileLock(resource_path, lock_dir)

    # Mock the logger call directly as caplog is unreliable with your logging setup.
    mock_log_warning = MagicMock()
    # Replace the logger's .warning method with our mock
    # Path: docbuild.utils.pidlock.log.warning
    monkeypatch.setattr('docbuild.utils.pidlock.log.warning', mock_log_warning)

    lock.acquire()

    # Assertion: Check if our mock was called with the expected warning message.
    expected_message_start = 'Lock file at'
    expected_message_end = 'contains invalid PID. Removing and retrying.'

    warning_found = False
    for call in mock_log_warning.call_args_list:
        # Check if the first argument (the log message string) contains the expected text
        if expected_message_start in call[0][0] and expected_message_end in call[0][0]:
            warning_found = True
            break

    # Assert that the warning was logged (via the mock)
    assert warning_found, f'Expected warning message not found in log calls.'

    # Verify the lock was successfully acquired after cleanup and retry
    assert lock.lock is True
    assert lock.lock_path.read_text().strip() == str(os.getpid())
    lock.release()

    # --- Scenario 2: FileNotFoundError (Race Condition) ---
    # 1. Create a stale lock file with a cleanable PID
    stale_pid = 9999
    lock_path.write_text(str(stale_pid))

    # 2. Mock Path.unlink() to raise FileNotFoundError on the first call

    # Patch the class method using monkeypatch to avoid the 'read-only' AttributeError.

    # Store the original class method
    original_posix_path_unlink = PosixPath.unlink

    class UnlinkMockState:
        first_call = True

    def mocked_posix_path_unlink(self, missing_ok=False):
        """Simulates the file being removed by another process on the first try."""
        if UnlinkMockState.first_call:
            UnlinkMockState.first_call = False
            # We don't need to restore here; the automatic retry inside PidFileLock
            # will see the original method restored by the end of the lock.acquire() call,
            # but we need to ensure the *retry* succeeds, so we patch to call the original
            # on the second attempt (though the recursive nature of acquire makes this tricky).

            # The simplest way is to raise the error once and let the logic handle the retry.
            raise FileNotFoundError(f'Mocked race: {self}')

        # If the code reaches here (a subsequent unlink attempt), call the original method.
        # Note: The recursive acquire() should create a new lock instance, which
        # may not hit this mocked code again if the previous patch was on the instance.
        # Since we patch the CLASS, the second attempt in the retry loop will hit
        # the original method if the lock is successfully acquired and then released later
        # during the test's cleanup, but for the actual acquisition retry,
        # it will continue using the patch until the lock is acquired.

        # The logic inside PidFileLock handles the retry, so for simplicity in the mock:
        return original_posix_path_unlink(self, missing_ok=missing_ok)

    # Patch the CLASS METHOD using monkeypatch. This is safe and fixes the teardown error.
    monkeypatch.setattr(PosixPath, 'unlink', mocked_posix_path_unlink)

    # Acquire should attempt cleanup, hit FileNotFoundError (due to mock), and retry successfully.
    lock_race = PidFileLock(resource_path, lock_dir)
    lock_race.acquire()

    # Verify acquisition succeeded despite the mocked race error
    assert lock_race.lock is True
    assert lock_race.lock_path.exists()
    assert lock_race.lock_path.read_text().strip() == str(os.getpid())
    lock_race.release()


def test_concurrent_instance_raises_runtime_error(lock_setup, mock_pid_running):
    """Test that acquiring a lock for an already running process raises RuntimeError."""
    resource_path, lock_dir = lock_setup
    lock_dir.mkdir()

    # 1. Manually create a running lock file with the mocked PID
    running_pid = 12345
    lock_path = PidFileLock(resource_path, lock_dir).lock_path
    lock_path.write_text(str(running_pid))

    # 2. Attempt to acquire the lock and expect failure
    lock = PidFileLock(resource_path, lock_dir)
    with pytest.raises(RuntimeError) as excinfo:
        lock.acquire()

    # 3. Verify the error message is correct
    assert f'docbuild instance already running (PID: {running_pid})' in str(
        excinfo.value
    )

    # 4. Verify the lock was NOT acquired or removed
    assert lock.lock is False
    assert lock_path.exists()
    assert lock_path.read_text().strip() == str(running_pid)


@patch('docbuild.utils.pidlock.atexit')
def test_lock_release_cleans_up_atexit_registration(mock_atexit, lock_setup):
    """Test that the lock is cleaned up properly, especially the atexit registration."""
    resource_path, lock_dir = lock_setup

    # Manually acquire the lock without using context manager
    lock = PidFileLock(resource_path, lock_dir)

    # Mock the register call *before* acquire is run
    # This ensures that when lock.acquire() calls atexit.register, it uses our mock.
    mock_atexit.register.reset_mock()  # Clear any previous calls from test setup/teardown
    lock.acquire()

    # Manually release the lock
    lock.release()

    # Check that both register (in acquire) and unregister (in release) were called.
    mock_atexit.register.assert_called_once_with(lock.release)
    mock_atexit.unregister.assert_called_once_with(lock.release)

    # Check lock state
    assert lock.lock is False
    assert not lock.lock_path.exists()


def test_lock_acquiring_without_dir_exists(lock_setup):
    """Test acquiring the lock when the lock directory does not yet exist."""
    resource_path, lock_dir = lock_setup

    # Ensure lock_dir is deleted if it exists
    if lock_dir.exists():
        shutil.rmtree(lock_dir)

    lock = PidFileLock(resource_path, lock_dir)
    with lock:
        assert lock.lock is True
        assert lock.lock_path.exists()
        assert lock_dir.is_dir()  # Verify directory was created

    assert not lock.lock_path.exists()
