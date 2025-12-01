"""Tests for the PidFileLock utility."""

import errno
import logging
import multiprocessing as mp
from multiprocessing import Event
import os
from pathlib import Path
import platform
import time

import pytest
from unittest.mock import patch, Mock
import docbuild.utils.pidlock as pidlock_mod
import builtins
from docbuild.utils.pidlock import LockAcquisitionError, PidFileLock

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


def test_pidfilelock_singleton_per_lock_path(tmp_path):
    """Constructing PidFileLock twice for the same resource should return the same instance."""
    resource = tmp_path / "resource.txt"
    lock_dir = tmp_path / "locks"

    lock1 = PidFileLock(resource, lock_dir=lock_dir)
    lock2 = PidFileLock(resource, lock_dir=lock_dir)

    # same computed lock_path and same object returned
    assert lock1 is lock2
    assert lock1.lock_path == lock2.lock_path


def test_flock_eagain_raises_lockacquisitionerror(tmp_path):
    """If fcntl.flock raises EAGAIN/EWOULDBLOCK, a LockAcquisitionError is raised
    and the module's cleanup path (closing the opened handle) is executed.
    Use a real file handle (no patch of open) so the actual close() source line
    in pidlock.py is executed and counted by coverage.
    """
    resource = tmp_path / "resource.txt"
    lock_dir = tmp_path / "locks"
    lock_dir.mkdir()

    def raise_eagain(fd, op):
        raise OSError(errno.EAGAIN, "Resource temporarily unavailable")

    # Only patch the flock call; let pidlock.open create a real file handle so
    # the except branch that calls handle.close() runs in pidlock.py.
    with patch.object(pidlock_mod.fcntl, "flock", raise_eagain):
        with pytest.raises(LockAcquisitionError):
            with PidFileLock(resource, lock_dir=lock_dir):
                pass


def test_open_eacces_raises_runtimeerror(tmp_path):
    """If opening the lock file fails with EACCES/EPERM, a RuntimeError is raised."""
    resource = tmp_path / "resource.txt"
    lock_dir = tmp_path / "locks"

    def fake_open(*args, **kwargs):
        raise OSError(errno.EACCES, "Permission denied")

    with patch.object(pidlock_mod, "open", fake_open):
        with pytest.raises(RuntimeError, match="Cannot acquire lock"):
            with PidFileLock(resource, lock_dir=lock_dir):
                pass


def test_open_eacces_raises_runtimeerror_via_builtins(tmp_path):
    """Ensure the EACCES/EPERM open failure branch raises RuntimeError (covers the raise RuntimeError line)."""
    resource = tmp_path / "resource.txt"
    lock_dir = tmp_path / "locks"
    lock_dir.mkdir()
    resource.write_text("dummy")
    lock = PidFileLock(resource, lock_dir)

    def fake_open(*args, **kwargs):
        raise OSError(errno.EACCES, "Permission denied (simulated)")

    # Patch the actual builtins.open used by pidlock.open(...) to ensure the except branch is hit
    with patch.object(builtins, "open", fake_open):
        with pytest.raises(RuntimeError, match="Cannot acquire lock"):
            with lock:
                pass


def test_open_other_oserror_reraises_original_exception(tmp_path):
    """If open() raises an OSError not handled by special branches, it should be re-raised."""
    resource = tmp_path / "resource.txt"
    lock_dir = tmp_path / "locks"

    def fake_open(*args, **kwargs):
        raise OSError(errno.EINVAL, "Invalid argument")

    with patch.object(pidlock_mod, "open", fake_open):
        with pytest.raises(OSError) as excinfo:
            with PidFileLock(resource, lock_dir=lock_dir):
                pass

    # Ensure the original errno is preserved (covers the final `raise e` branch)
    assert excinfo.value.errno == errno.EINVAL


def test_enter_handles_flock_eagain_closes_handle(tmp_path):
    """When flock raises EAGAIN after open succeeded, the opened handle is closed and LockAcquisitionError is raised."""
    resource = tmp_path / "resource.txt"
    lock_dir = tmp_path / "locks"
    # Create fake handle and ensure it has a close() we can assert
    fake_handle = Mock()
    fake_handle.fileno.return_value = 123
    fake_handle.seek.return_value = None
    fake_handle.truncate.return_value = None
    fake_handle.write.return_value = None
    fake_handle.flush.return_value = None
    fake_handle.close.return_value = None

    def raise_eagain(fd, op):
        raise OSError(errno.EAGAIN, "Resource temporarily unavailable")

    with patch.object(pidlock_mod, "open", lambda *a, **k: fake_handle):
        with patch.object(pidlock_mod.fcntl, "flock", raise_eagain):
            with pytest.raises(LockAcquisitionError):
                with PidFileLock(resource, lock_dir=lock_dir):
                    pass

    fake_handle.close.assert_called_once()


def test_enter_open_eacces_raises_runtimeerror(tmp_path):
    """If module-level open raises EACCES, __enter__ raises a RuntimeError wrapping that OSError."""
    resource = tmp_path / "resource.txt"
    lock_dir = tmp_path / "locks"

    def fake_open(*args, **kwargs):
        raise OSError(errno.EACCES, "Permission denied (simulated)")

    with patch.object(pidlock_mod, "open", fake_open):
        with pytest.raises(RuntimeError, match="Cannot acquire lock"):
            with PidFileLock(resource, lock_dir=lock_dir):
                pass


def test_exit_flock_unlock_oserror_is_handled(tmp_path):
    """If releasing the fcntl lock (second flock call) raises OSError, __exit__ should catch and log but not raise."""
    resource = tmp_path / "resource.txt"
    lock_dir = tmp_path / "locks"
    lock_dir.mkdir()
    calls = {"n": 0}

    def flock_first_ok_then_raise(fd, op):
        calls["n"] += 1
        if calls["n"] == 1:
            return None  # __enter__ flock succeeds
        # second call (unlock) raises
        raise OSError(errno.EIO, "I/O error on unlock")

    with patch.object(pidlock_mod.fcntl, "flock", flock_first_ok_then_raise):
        # Should not raise on context exit even though unlock raises
        with PidFileLock(resource, lock_dir=lock_dir):
            assert Path(lock_dir).exists()
        # after exit, lock file cleaned up (unlink missing_ok may remove it)
        assert not PidFileLock(resource, lock_dir).lock_path.exists()


def test_exit_handle_close_raises_is_handled(tmp_path):
    """If handle.close() raises OSError, __exit__ should catch and log and continue cleanup."""
    resource = tmp_path / "resource.txt"
    lock_dir = tmp_path / "locks"
    lock_dir.mkdir()

    # fake handle whose close() will raise OSError
    class BadHandle:
        def fileno(self):
            return 1
        def seek(self, *_):
            return None
        def truncate(self, *_):
            return None
        def write(self, *_):
            return None
        def flush(self):
            return None
        def close(self):
            raise OSError(errno.EIO, "close failed")

    bad_handle = BadHandle()

    # Make flock a no-op so __enter__ succeeds
    with patch.object(pidlock_mod.fcntl, "flock", lambda *a, **k: None):
        with patch.object(pidlock_mod, "open", lambda *a, **k: bad_handle):
            # Should not raise on context exit despite close() raising
            with PidFileLock(resource, lock_dir=lock_dir):
                pass


def test_exit_unlink_raises_oserror_is_handled(tmp_path):
    """If unlink() raises OSError during __exit__, it should be caught and logged without raising."""
    resource = tmp_path / "resource.txt"
    lock_dir = tmp_path / "locks"
    lock_dir.mkdir()

    # Use a normal file handle and normal flock to acquire lock
    with patch.object(pidlock_mod.fcntl, "flock", lambda *a, **k: None):
        lock = PidFileLock(resource, lock_dir=lock_dir)

        # Patch the Path.unlink implementation used by pidlock so unlink() raises OSError
        def bad_unlink(self, missing_ok=True):
            raise OSError(errno.EIO, "unlink failed")

        with patch.object(pidlock_mod.Path, "unlink", bad_unlink):
            # enter the context; when __exit__ calls unlink(), it will raise and be handled
            with lock:
                pass

    # exit should not raise even though unlink raised
    assert not lock._lock_acquired
    assert lock._handle is None


def test_enter_open_eacces_on_fresh_instance(tmp_path):
    """Force the EACCES/EPERM branch on a fresh PidFileLock instance to cover the RuntimeError path."""
    resource = tmp_path / "resource_eacces.txt"
    lock_dir = tmp_path / "locks_eacces"

    def fake_open(*args, **kwargs):
        raise OSError(errno.EACCES, "Permission denied (forced)")

    # Patch the module-level open used by pidlock for this fresh instance
    with patch.object(pidlock_mod, "open", fake_open):
        with pytest.raises(RuntimeError, match="Cannot acquire lock"):
            with PidFileLock(resource, lock_dir=lock_dir):
                pass


def test_enter_flock_eagain_no_handle(tmp_path):
    """
    Simulate EAGAIN/EWOULDBLOCK being raised when 'handle' is None to hit the
    'if handle: handle.close()' branch where 'handle' is None.
    """

    resource = tmp_path / 'resource.txt'
    lock_dir = tmp_path / 'locks'

    # Mock open to return a handle
    real_handle = open(tmp_path / 'lockfile.tmp', 'w+')

    # Using two mocks: one for open to succeed, one for flock to fail.
    # Patch 'open' in a way that allows controlling the assignment of 'handle'.

    # Simulate open failing with EAGAIN directly, which also forces 'handle' to be None.
    def fake_open_with_eagain(*args, **kwargs):
        raise OSError(errno.EAGAIN, 'Simulated open error matching flock failure')

    with patch.object(pidlock_mod, 'open', fake_open_with_eagain):
        with pytest.raises(LockAcquisitionError, match='Resource is locked'):
            with PidFileLock(resource, lock_dir=lock_dir):
                pass
