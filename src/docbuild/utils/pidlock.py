"""PID file locking utility."""

import atexit
import hashlib
import logging
import sys
import os as _os  # renamed for safe monkeypatching
import errno
from pathlib import Path
from typing import TypeVar

from ..constants import BASE_LOCK_DIR

T = TypeVar("T", bound="PidFileLock")

log = logging.getLogger(__name__)
log.propagate = True  # Allow external capture (e.g., pytest's caplog)

class PidFileLock:
    """Manages a PID lock file to ensure only one instance of an environment runs."""

    lock_file: Path | None = None  # Exposed for testing and static type checkers
    os = _os  # Expose os under class for reliable monkeypatching in tests

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
        current_pid = self.os.getpid()

        while True:
            # Step 1: Try atomic creation
            try:
                lock_fd = self.os.open(
                    self.lock_path, self.os.O_WRONLY | self.os.O_CREAT | self.os.O_EXCL, 0o644
                )
                with open(lock_fd, "w") as f:
                    f.write(f"{current_pid}\n")
                self._lock_acquired = True
                self.lock_file = self.lock_path
                log.debug(f"Acquired lock for {self.resource_path} at PID {current_pid}.")
                atexit.register(self.release)
                return
            except FileExistsError:
                pass
            except OSError as e:
                raise RuntimeError(
                    "Same instance is already running. "
                    "Either wait until the first instance is complete or cancel it. "
                    f"PID={current_pid}, lock file at {self.lock_path}: {e}"
                )

            # Step 2: Handle existing lock file
            if not self.lock_path.exists():
                continue

            try:
                with self.lock_path.open("r") as f:
                    pid_str = f.read().strip()
                pid = int(pid_str)

                if self._is_pid_running(pid):
                    raise RuntimeError(
                        f"docbuild instance already running (PID: {pid}) "
                        f"for configuration: {self.resource_path}"
                    )

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
                try:
                    lock_fd = self.os.open(
                        self.lock_path, self.os.O_WRONLY | self.os.O_CREAT | self.os.O_EXCL, 0o644
                    )
                    with open(lock_fd, "w") as f:
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
        if not self._lock_acquired:
            return

        try:
            try:
                atexit.unregister(self.release)
            except (ValueError, AttributeError):
                pass

            # Safely remove the lock file
            if self.lock_path.exists():
                try:
                    self.lock_path.unlink()
                    # Only log if the interpreter is not finalizing
                    if not getattr(sys, "is_finalizing", lambda: False)():
                        log.debug("Released lock at %s.", self.lock_path)
                except OSError as e:
                    if not getattr(sys, "is_finalizing", lambda: False)():
                        log.error(f"Failed to remove lock file at {self.lock_path}: {e}")

        finally:
            self._lock_acquired = False
            self.lock_file = None


    @staticmethod
    def _is_pid_running(pid: int) -> bool:
        if pid <= 0:
            return False
        try:
            _os.kill(pid, 0)
            return True
        except OSError as err:
            return err.errno != errno.ESRCH
