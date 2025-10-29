"""PID file locking utility."""

import atexit
import hashlib
import logging
import os
import errno
from pathlib import Path
from typing import TypeVar

T = TypeVar("T", bound="PidFileLock")

from ..constants import BASE_LOCK_DIR

# --- Safe Logging Setup for CI / Pytest (prevents teardown ValueErrors) ---

class _SafeStreamHandler(logging.StreamHandler):
    """A logging handler that ignores 'I/O operation on closed file' errors during teardown."""
    def emit(self, record):
        try:
            super().emit(record)
        except ValueError as e:
            if "I/O operation on closed file" in str(e):
                # Ignore harmless teardown errors (common in Python 3.13 + pytest)
                return
            raise


log = logging.getLogger(__name__)
log.propagate = True  # Allow pytest's caplog to capture messages

# Apply safe handler in CI or pytest only
if os.getenv("CI") or os.getenv("PYTEST_CURRENT_TEST"):
    for h in list(log.handlers):
        log.removeHandler(h)
    _safe_handler = _SafeStreamHandler()
    _safe_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    log.addHandler(_safe_handler)
    log.propagate = False


# --- Core PID Lock Implementation ---

class PidFileLock:
    """Manages a PID lock file to ensure only one instance of an environment runs."""

    lock_file: Path | None = None  # Exposed for testing and static type checkers

    def __init__(self, resource_path: Path, lock_dir: Path = BASE_LOCK_DIR) -> None:
        self.resource_path = resource_path.resolve()
        self._lock_dir: Path = lock_dir
        self._lock_path: Path = self._generate_lock_name()
        self._lock_acquired: bool = False

    @property
    def lock_dir(self) -> Path:
        return self._lock_dir

    @property
    def lock_path(self) -> Path:
        return self._lock_path

    @property
    def lock(self) -> bool:
        return self._lock_acquired

    def __enter__(self: T) -> T:
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.release()

    def _generate_lock_name(self) -> Path:
        path_hash = hashlib.sha256(str(self.resource_path).encode("utf-8")).hexdigest()
        return self._lock_dir / f"docbuild-{path_hash}.pid"

    def acquire(self) -> None:
        """Acquire the lock atomically, or diagnose an existing lock."""
        self.lock_dir.mkdir(parents=True, exist_ok=True)
        current_pid = os.getpid()

        while True:
            # Step 1: Try atomic creation
            try:
                lock_fd = os.open(
                    self.lock_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644
                )
                with os.fdopen(lock_fd, "w") as f:
                    f.write(f"{current_pid}\n")
                self._lock_acquired = True
                self.lock_file = self.lock_path
                log.debug(f"Acquired lock for {self.resource_path} at PID {current_pid}.")
                atexit.register(self.release)
                return
            except FileExistsError:
                pass
            except OSError as e:
                raise RuntimeError(f"Failed to create lock file at {self.lock_path}: {e}")

            # Step 2: Handle existing lock file
            if not self.lock_path.exists():
                continue  # Retry loop

            try:
                with self.lock_path.open("r") as f:
                    pid_str = f.read().strip()
                pid = int(pid_str)

                if self._is_pid_running(pid):
                    raise RuntimeError(
                        f"docbuild instance already running (PID: {pid}) "
                        f"for configuration: {self.resource_path}"
                    )

                # Stale lock: clean and retry
                log.warning(
                    f"Found stale lock file at {self.lock_path} (PID {pid}). Removing and retrying acquisition."
                )
                self.lock_path.unlink()

            except (FileNotFoundError, ValueError):
                log.warning(
                    f"Lock file at {self.lock_path} missing or invalid. Removing and retrying."
                )
                self.lock_path.unlink(missing_ok=True)

            except OSError as e:
                log.error(f"Non-critical error while checking lock file: {e}")
                try:
                    self.lock_path.unlink(missing_ok=True)
                except Exception:
                    pass
                # Attempt one last atomic creation
                try:
                    lock_fd = os.open(
                        self.lock_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644
                    )
                    with os.fdopen(lock_fd, "w") as f:
                        f.write(f"{current_pid}\n")
                    self._lock_acquired = True
                    self.lock_file = self.lock_path
                    atexit.register(self.release)
                    return
                except Exception as e2:
                    raise RuntimeError(
                        f"Failed to recover from non-critical lock read error: {e2}"
                    )

    def release(self) -> None:
        """Release the lock file."""
        if self._lock_acquired and self.lock_path.exists():
            try:
                self.lock_path.unlink()
                self._lock_acquired = False
                self.lock_file = None
                log.debug("Released lock at %s.", self.lock_path)
                try:
                    atexit.unregister(self.release)
                except (ValueError, AttributeError):
                    log.debug("atexit.unregister failed or unavailable.")
            except OSError as e:
                log.error(f"Failed to remove lock file at {self.lock_path}: {e}")

    @staticmethod
    def _is_pid_running(pid: int) -> bool:
        if pid <= 0:
            return False
        try:
            os.kill(pid, 0)
            return True
        except OSError as err:
            return err.errno != errno.ESRCH
