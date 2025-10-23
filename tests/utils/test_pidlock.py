"""Tests for the PidFileLock utility."""

import errno
import logging
import os
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Need to mock atexit.unregister, which is called inside PidFileLock.release(). This is crucial for isolated testing.
import atexit 

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
        raise OSError(errno.ESRCH, "No such process")
    
    monkeypatch.setattr(os, "kill", mock_kill)

@pytest.fixture
def mock_pid_dead(monkeypatch):
    """
    Mocks os.kill to simulate a dead process (PID does not exist).
    """
    def mock_kill(pid, sig):
        # Always raise ESRCH (No such process) for any checked PID
        raise OSError(errno.ESRCH, "No such process")
        
    monkeypatch.setattr(os, "kill", mock_kill)


@pytest.fixture
def lock_setup(tmp_path: Path) -> tuple[Path, Path]:
    """Provides a resource path and the temporary lock directory."""
    resource_path = tmp_path / "env.production.toml"
    resource_path.touch()  # The resource path must exist
    lock_dir = tmp_path / "locks"
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
    """Test that a stale (dead process) lock is removed and a new one is acquired."""
    resource_path, lock_dir = lock_setup
    lock_dir.mkdir()
    
    # 1. Manually create a stale lock file with a fake PID
    stale_pid = 9999
    lock_path = PidFileLock(resource_path, lock_dir).lock_path
    lock_path.write_text(str(stale_pid))
    
    # 2. Attempt to acquire the lock
    lock = PidFileLock(resource_path, lock_dir)
    # We acquire the lock and then manually release it later in the test teardown
    lock.acquire()
    
    # 3. Verify the stale lock was removed and a new one was acquired
    assert lock.lock is True
    assert lock.lock_path.exists()
    assert lock.lock_path.read_text().strip() == str(os.getpid())
    log.info("Stale lock successfully cleaned and re-acquired.")


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
    assert f"docbuild instance already running (PID: {running_pid})" in str(excinfo.value)
    
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
    mock_atexit.register.reset_mock() # Clear any previous calls from test setup/teardown
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
        assert lock_dir.is_dir() # Verify directory was created
    
    assert not lock.lock_path.exists()
