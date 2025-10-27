"""PID file locking utility."""

import atexit
import hashlib
import logging
import os
from pathlib import Path
from typing import Self, Any

from ..constants import BASE_LOCK_DIR

log = logging.getLogger(__name__)


class PidFileLock:
    """Manages a PID lock file to ensure only one instance of an environment runs.

    The lock file is named based on a hash of the environment config file path.
    """

    def __init__(self, resource_path: Path, lock_dir: Path = BASE_LOCK_DIR) -> None:
        """Initialize the lock manager.

        :param resource_path: The unique path identifying the resource to lock (e.g., env config file).
        :param lock_dir: The base directory for lock files.
        """
        self.resource_path = resource_path.resolve()
        self._lock_dir: Path = lock_dir
        self._lock_path: Path = self._generate_lock_name()
        self._lock_acquired: bool = False

    @property
    def lock_dir(self) -> Path:
        """The directory where PID lock files are stored."""
        return self._lock_dir

    @property
    def lock_path(self) -> Path:
        """The full path to the lock file."""
        return self._lock_path

    @property
    def lock(self) -> bool:
        """Return the current lock acquisition state."""
        return self._lock_acquired

    def __enter__(self) -> Self:
        """Acquire the lock."""
        self.acquire()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: Any,
    ) -> None:
        """Release the lock."""
        self.release()

    def _generate_lock_name(self) -> Path:
        """Generate a unique lock file name based on the resource path."""
        path_hash = hashlib.sha256(str(self.resource_path).encode("utf-8")).hexdigest()
        return self._lock_dir / f"docbuild-{path_hash}.pid"

    def acquire(self) -> None:
        """Acquire the lock atomically, or diagnose an existing lock."""
        self.lock_dir.mkdir(parents=True, exist_ok=True)
        current_pid = os.getpid()

        try:
            lock_fd = os.open(
                self.lock_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644
            )
            with os.fdopen(lock_fd, "w") as f:
                f.write(f"{current_pid}\n")

            self._lock_acquired = True
            try:
                if logging.getLogger().hasHandlers() and not logging._shutdown:
                    log.debug("Acquired lock for %s (PID %s).", self.resource_path, current_pid)
            except Exception:
                pass

            atexit.register(self.release)
            return

        except FileExistsError:
            pass
        except OSError as e:
            raise RuntimeError(f"Failed to create lock file at {self.lock_path}: {e}")

        if self.lock_path.exists():
            try:
                with self.lock_path.open("r") as f:
                    pid_str = f.read().strip()
                pid = int(pid_str)

                if self._is_pid_running(pid):
                    raise RuntimeError(
                        f"docbuild instance already running (PID: {pid}) "
                        f"for configuration: {self.resource_path}"
                    )
                else:
                    try:
                        if logging.getLogger().hasHandlers() and not logging._shutdown:
                            log.warning(
                                "Found stale lock file at %s (PID %s). Removing and retrying acquisition.",
                                self.lock_path,
                                pid,
                            )
                    except Exception:
                        pass
                    self.lock_path.unlink()
                    return self.acquire()

            except FileNotFoundError:
                return self.acquire()
            except ValueError:
                try:
                    if logging.getLogger().hasHandlers() and not logging._shutdown:
                        log.warning(
                            "Lock file at %s contains invalid PID. Removing and retrying.",
                            self.lock_path,
                        )
                except Exception:
                    pass
                self.lock_path.unlink()
                return self.acquire()
            except OSError as e:
                try:
                    if logging.getLogger().hasHandlers() and not logging._shutdown:
                        log.error("Non-critical error while checking lock file: %s", e)
                except Exception:
                    pass

        raise RuntimeError(f"Failed to acquire lock for {self.resource_path} after multiple checks.")

    def release(self) -> None:
        """Release the lock file."""
        if self._lock_acquired and self.lock_path.exists():
            try:
                self.lock_path.unlink()
                self._lock_acquired = False

                # Only log if logging system is active
                try:
                    if logging.getLogger().hasHandlers() and not logging._shutdown:
                        log.debug("Released lock at %s.", self.lock_path)
                except Exception:
                    pass

                # Unregister the cleanup hook safely
                try:
                    atexit.unregister(self.release)
                except Exception:
                    pass

            except OSError as e:
                try:
                    if logging.getLogger().hasHandlers() and not logging._shutdown:
                        log.error(f"Failed to remove lock file at {self.lock_path}: {e}")
                except Exception:
                    pass

    @staticmethod
    def _is_pid_running(pid: int) -> bool:
        """Check whether a given PID is currently running."""
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        else:
            return True
