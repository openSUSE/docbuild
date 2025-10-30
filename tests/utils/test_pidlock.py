"""Tests for the PidFileLock utility."""

import os
import errno
import pytest
import logging
from pathlib import Path
from docbuild.utils.pidlock import PidFileLock


@pytest.fixture
def lock_setup(tmp_path):
    resource_file = tmp_path / "env.production.toml"
    resource_file.write_text("[dummy]\nkey=value")
    lock_dir = tmp_path / "locks"
    return resource_file, lock_dir


def test_acquire_and_release_creates_lock_file(lock_setup):
    resource_path, lock_dir = lock_setup
    lock_dir.mkdir()
    lock = PidFileLock(resource_path, lock_dir)

    # Acquire lock using context manager
    with lock:
        assert lock.lock_path.exists()
        assert lock.lock

    # After context manager, lock should be released
    assert not lock.lock_path.exists()
    assert not lock.lock


def test_context_manager(lock_setup):
    resource_path, lock_dir = lock_setup
    lock_dir.mkdir()
    with PidFileLock(resource_path, lock_dir) as lock:
        assert lock.lock
        assert lock.lock_path.exists()
    # After exit, lock should be released
    assert not lock.lock_path.exists()
    assert not lock.lock


def test_double_acquire_raises(lock_setup):
    resource_path, lock_dir = lock_setup
    lock_dir.mkdir()
    lock = PidFileLock(resource_path, lock_dir)

    lock.acquire()
    with pytest.raises(RuntimeError):
        lock.acquire()
    lock.release()


def test_stale_lock_is_cleaned_up(lock_setup):
    resource_path, lock_dir = lock_setup
    lock_dir.mkdir()
    lock = PidFileLock(resource_path, lock_dir)
    lock.lock_path.write_text("999999")  # Fake PID

    with lock:
        assert lock.lock_path.exists()
        assert lock.lock

    assert not lock.lock_path.exists()
    assert not lock.lock


def test_acquire_with_invalid_pid_file(lock_setup):
    """Test acquire when lock file exists but contains invalid PID."""
    resource_path, lock_dir = lock_setup
    lock_dir.mkdir()
    lock = PidFileLock(resource_path, lock_dir)
    lock.lock_path.write_text("notanumber")

    with lock:
        assert lock.lock_path.exists()
        assert lock.lock

    assert not lock.lock_path.exists()
    assert not lock.lock


def test_acquire_non_critical_oserror_on_read(lock_setup, monkeypatch):
    resource_path, lock_dir = lock_setup
    lock_dir.mkdir()
    lock = PidFileLock(resource_path, lock_dir)
    lock.lock_path.write_text("9999")

    original_open = Path.open

    def mocked_open(self, mode="r", *args, **kwargs):
        if "r" in mode:
            raise OSError(errno.EACCES, "Permission denied during read")
        return original_open(self, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", mocked_open)

    logger = logging.getLogger("docbuild.utils.pidlock")
    log_messages = []

    class CaptureHandler(logging.Handler):
        def emit(self, record):
            log_messages.append(self.format(record))

    handler = CaptureHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.ERROR)

    with lock:
        pass

    logger.removeHandler(handler)
    assert any("Non-critical error while checking lock file" in msg for msg in log_messages)


def test_release_without_acquire(lock_setup):
    """Releasing a lock that was never acquired should be safe."""
    resource_path, lock_dir = lock_setup
    lock_dir.mkdir()
    lock = PidFileLock(resource_path, lock_dir)
    lock.release()  # Should not raise
    assert not lock.lock
    assert not lock.lock_path.exists()


def test_release_with_unlink_error(lock_setup, monkeypatch):
    """Simulate OSError during unlink to cover exception branch in release."""
    resource_path, lock_dir = lock_setup
    lock_dir.mkdir()
    lock = PidFileLock(resource_path, lock_dir)

    with lock:
        def mocked_unlink(path):
            raise OSError(errno.EACCES, "Permission denied")

        monkeypatch.setattr(os, "unlink", mocked_unlink)
        # Release should log error but not raise
        lock.release()

    # Internal state should be cleared even if unlink failed
    assert not lock.lock
    assert lock.lock_file is None


def test_acquire_noncritical_oserror(monkeypatch, tmp_path):
    """Simulate non-critical OS error (EPERM) during acquire."""
    lock_dir = tmp_path / "locks"
    lock_dir.mkdir()
    lock_file = tmp_path / "resource.txt"
    lock = PidFileLock(lock_file, lock_dir)

    def mocked_os_open(path, flags, *args, **kwargs):
        if flags & os.O_WRONLY:
            raise OSError(errno.EPERM, "Permission denied")
        return os.open(path, flags, *args, **kwargs)

    monkeypatch.setattr(os, "open", mocked_os_open)

    with pytest.raises(RuntimeError) as exc_info:
        lock.acquire()

    assert "Permission denied" in str(exc_info.value)


def test_acquire_critical_oserror(monkeypatch, tmp_path):
    """Simulate critical OS error (EACCES) during acquire."""
    lock_dir = tmp_path / "locks"
    lock_dir.mkdir()
    lock_file = tmp_path / "resource.txt"
    lock = PidFileLock(lock_file, lock_dir)

    def mocked_os_open(path, flags, *args, **kwargs):
        raise OSError(errno.EACCES, "Access denied")

    monkeypatch.setattr(os, "open", mocked_os_open)

    with pytest.raises(RuntimeError) as exc_info:
        lock.acquire()

    assert "Access denied" in str(exc_info.value)


def test_acquire_when_lock_dir_missing(tmp_path):
    """If lock directory does not exist, it should be created automatically."""
    resource_file = tmp_path / "res.txt"
    resource_file.write_text("dummy")
    lock_dir = tmp_path / "locks"
    lock = PidFileLock(resource_file, lock_dir)

    with lock:
        assert lock.lock_path.exists()
        assert lock.lock

    assert not lock.lock_path.exists()
    assert not lock.lock
