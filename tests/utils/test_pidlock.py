"""Tests for the PidFileLock utility."""

import errno
import os
import pytest
import logging
import multiprocessing as mp
import time
import platform
from pathlib import Path
from docbuild.utils.pidlock import PidFileLock, LockAcquisitionError
from multiprocessing import Event

# Define a shared marker to skip the test if the OS is macOS (Darwin)
skip_macos = pytest.mark.skipif(
    platform.system() == "Darwin",
    reason="Skipped on macOS due to known multiprocessing/resource cleanup issues.",
)

@pytest.fixture
def lock_setup(tmp_path):
    """Fixture to create a dummy resource file and lock directory."""
    resource_file = tmp_path / "env.production.toml"
    resource_file.write_text("[dummy]\nkey=value")
    lock_dir = tmp_path / "locks"
    return resource_file, lock_dir


# --- Helper function for multiprocessing tests (Must be top-level/global) ---

def _mp_lock_holder(resource_path: Path, lock_dir: Path, lock_path: Path, done_event: Event): # type: ignore
    """Acquire and hold a lock in a separate process, waiting for an event to release."""
    lock = PidFileLock(resource_path, lock_dir)
    try:
        with lock:
            lock_path.touch()
            done_event.wait()
            
    except Exception:
        pass


# -----------------------------------------------------------------------------
# Core PidFileLock Tests
# -----------------------------------------------------------------------------

def test_acquire_and_release_creates_lock_file(lock_setup):
    """Test that the lock file is created on entry and removed on exit."""
    resource_path, lock_dir = lock_setup
    lock_dir.mkdir()
    lock = PidFileLock(resource_path, lock_dir)

    with lock:
        # Lock file should exist while the lock is held
        assert lock.lock_path.exists()

    # Lock file must be cleaned up on __exit__
    assert not lock.lock_path.exists()


def test_context_manager(lock_setup):
    """Simple test for the context manager usage."""
    resource_path, lock_dir = lock_setup
    lock_dir.mkdir()

    with PidFileLock(resource_path, lock_dir) as lock:
        assert lock.lock_path.exists()

    assert not lock.lock_path.exists()


@skip_macos 
def test_lock_prevents_concurrent_access_in_separate_process(lock_setup):
    """Test that two separate processes cannot acquire the same lock simultaneously."""

    resource_path, lock_dir = lock_setup
    lock_dir.mkdir()
    lock_path = PidFileLock(resource_path, lock_dir).lock_path

    # Create an Event to signal the child process to release the lock
    done_event = mp.Event()

    # Start a background process to hold the lock
    lock_holder = mp.Process(
        target=_mp_lock_holder,
        args=(resource_path, lock_dir, lock_path, done_event)
    )
    lock_holder.start()

    # Wait for the lock holder to acquire the lock (check for lock file existence)
    timeout_start = time.time()
    while not lock_path.exists():
        if time.time() - timeout_start > 5:
             raise TimeoutError("Child process failed to acquire lock in time.")
        time.sleep(0.01)

    # Main thread tries to acquire the same lock (EXPECT FAILURE)
    lock_attempt = PidFileLock(resource_path, lock_dir)
    with pytest.raises(LockAcquisitionError):
        with lock_attempt:
            pass

    # Cleanup: Signal the child process to exit cleanly and wait for it
    done_event.set()
    lock_holder.join(timeout=10) # Wait for clean exit (no need for terminate)

    # Final check: Ensure the child exited successfully
    if lock_holder.is_alive():
        # If it didn't exit, terminate it as a last resort (should not happen)
        lock_holder.terminate()
        lock_holder.join()

    # The lock should have been released cleanly by the child process's __exit__
    assert not lock_path.exists()


def test_lock_is_reentrant_per_process(lock_setup):
    """
    Test that the per-path singleton behavior works and prevents double acquisition
    using the new internal RuntimeError check.
    """
    resource_path, lock_dir = lock_setup
    lock_dir.mkdir()

    lock1 = PidFileLock(resource_path, lock_dir)
    lock2 = PidFileLock(resource_path, lock_dir)

    assert lock1 is lock2 # Same instance

    with lock1:
        # Second attempt to enter the context should raise RuntimeError (internal API misuse)
        with pytest.raises(RuntimeError, match="Lock already acquired by this PidFileLock instance."):
            with lock2:
                pass

    assert not lock1.lock_path.exists()


def test_acquire_when_lock_dir_missing(lock_setup):
    """Test that the lock directory is created automatically."""
    resource_path, lock_dir = lock_setup
    # lock_dir is *not* created here

    lock = PidFileLock(resource_path, lock_dir)

    with lock:
        # Check using the directory's path derived from lock_path
        assert lock.lock_path.parent.is_dir()
        assert lock.lock_path.exists()

    assert not lock.lock_path.exists()


def test_release_handles_missing_file_on_unlink(lock_setup):
    """Test that __exit__ does not raise if the file is already gone."""
    resource_path, lock_dir = lock_setup
    lock_dir.mkdir()
    lock = PidFileLock(resource_path, lock_dir)

    with lock:
        # Manually delete the lock file while the lock is still held (by the handle)
        lock.lock_path.unlink()

    # __exit__ should run without raising an error due to missing_ok=True
    assert not lock.lock_path.exists()


def test_acquire_critical_oserror(monkeypatch, tmp_path):
    """Test critical OSError (e.g., EACCES on open) raises RuntimeError."""
    lock_dir = tmp_path / "locks"
    lock_dir.mkdir()
    lock_file = tmp_path / "resource.txt"
    lock_file.write_text("dummy")
    lock = PidFileLock(lock_file, lock_dir)

    # Mock the built-in open to fail with EACCES, simulating a permissions error
    def mocked_builtin_open(path, mode):
        # We now rely on monkeypatching os.open directly in pidlock.py, 
        # but for this test, we mock builtins.open if os.open is not used directly.
        # Since pidlock.py now uses open(self._lock_path, 'w+'), mocking builtins.open is correct
        raise OSError(errno.EACCES, "Access denied")

    monkeypatch.setattr("builtins.open", mocked_builtin_open)

    with pytest.raises(RuntimeError) as exc_info:
        with lock:
            pass

    # Check that the RuntimeError message contains the expected text
    error_message = str(exc_info.value)
    assert "Cannot acquire lock:" in error_message
    assert "Access denied" in error_message