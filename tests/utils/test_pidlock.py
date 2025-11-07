"""Tests for the PidFileLock utility."""

import errno
import os
import pytest
import logging
import multiprocessing as mp
import time
from pathlib import Path
from docbuild.utils.pidlock import PidFileLock, LockAcquisitionError


@pytest.fixture
def lock_setup(tmp_path):
    """Fixture to create a dummy resource file and lock directory."""
    resource_file = tmp_path / "env.production.toml"
    resource_file.write_text("[dummy]\nkey=value")
    lock_dir = tmp_path / "locks"
    return resource_file, lock_dir


# --- Helper function for multiprocessing tests (Must be top-level/global) ---

def _mp_lock_holder(resource_path: Path, lock_dir: Path, lock_path: Path):
    """Acquire and hold a lock in a separate process."""
    lock = PidFileLock(resource_path, lock_dir)
    try:
        with lock:
            # Signal that lock is held
            lock_path.touch()
            # Hold for a long time
            time.sleep(10) 
    except LockAcquisitionError:
        # Expected if it fails to acquire
        pass
    except Exception:
        # Prevent multiprocessing from crashing noisily
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


def test_lock_prevents_concurrent_access_in_separate_process(lock_setup):
    """
    Test that a second process fails to acquire the lock.
    Uses the top-level helper function to avoid pickling errors.
    """
    pytest.skip("Temporarily skipping known hanging multiprocessing test on macOS CI.")
    
    resource_path, lock_dir = lock_setup
    lock_dir.mkdir()
    lock_path = PidFileLock(resource_path, lock_dir).lock_path

    # Start a background process to hold the lock
    lock_holder = mp.Process(target=_mp_lock_holder, args=(resource_path, lock_dir, lock_path))
    lock_holder.start()
    
    # Wait for the lock holder to acquire the lock (check for lock file existence)
    # The helper touches the file ONLY after acquiring the lock.
    while not lock_path.exists():
        time.sleep(0.01)

    # Main thread tries to acquire the same lock
    lock_attempt = PidFileLock(resource_path, lock_dir)
    with pytest.raises(LockAcquisitionError):
        with lock_attempt:
            pass # Should fail here

    # Cleanup the background process
    lock_holder.terminate()
    lock_holder.join()
    
    # Manual cleanup for the terminated process (since terminate prevents clean __exit__)
    if lock_path.exists():
        os.remove(lock_path)


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
    
    # Mock os.open to fail with EACCES during the critical step
    def mocked_os_open(path, flags, *args, **kwargs):
        if path == lock.lock_path:
            raise OSError(errno.EACCES, "Access denied")
        return os.open(path, flags, *args, **kwargs)

    monkeypatch.setattr(os, "open", mocked_os_open)

    with pytest.raises(RuntimeError) as exc_info:
        with lock:
            pass

    # Checks for the key phrases since the errno might be included
    error_message = str(exc_info.value)
    assert "Cannot acquire lock:" in error_message
    assert "Access denied" in error_message