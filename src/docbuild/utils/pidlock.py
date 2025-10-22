"""PID file locking utility."""

import atexit
import hashlib
import logging
import os
import errno
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
        self.lock_dir = lock_dir
        # The lock_path is already calculated here, fixing the AttributeError in test_acquire_and_release_success
        self.lock_path: Path = self._generate_lock_name() 
        self._lock_acquired: bool = False

    def __enter__(self) -> Self:
        """Acquire the lock."""
        self.acquire()
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: Any
    ) -> None:
        """Release the lock."""
        self.release()

    def _generate_lock_name(self) -> Path:
        """Generate a unique lock file name based on the resource path."""
        # SHA256 hash of the absolute path is used to ensure a unique, safe filename.
        path_hash = hashlib.sha256(str(self.resource_path).encode('utf-8')).hexdigest()
        return self.lock_dir / f'docbuild-{path_hash}.pid'

    def acquire(self) -> None:
        """Acquire the lock or raise an error if another instance is running."""
        self.lock_dir.mkdir(parents=True, exist_ok=True)
        current_pid = os.getpid()

        # 1. Check for stale lock
        if self.lock_path.exists():
            try:
                # Read PID from the file
                with self.lock_path.open('r') as f:
                    pid_str = f.read().strip()
                
                # Check if the process is actually running
                if pid_str and self._is_pid_running(int(pid_str)):
                    # A running instance exists. Reraise the RuntimeError!
                    raise RuntimeError(
                        f"docbuild instance already running (PID: {pid_str}) "
                        f"for configuration: {self.resource_path}"
                    )
                else:
                    # Stale lock: file exists but process is dead. Remove it.
                    log.warning(
                        f"Found stale lock file at {self.lock_path} (PID {pid_str}). Removing."
                    )
                    self.lock_path.unlink()
            
            # Only catch I/O errors that prevent reading/unlinking the lock file.
            # The RuntimeError for the running process check must propagate.
            except FileNotFoundError:
                # File was removed between exists() and open(). Continue.
                pass
            except OSError as e: 
                # Catching OSError for general I/O problems during read/unlink
                log.error(f"Non-critical error while checking lock file: {e}")
                pass 
            except ValueError:
                # Catching ValueError if the PID file content is not an integer
                log.warning(f"Lock file at {self.lock_path} contains invalid PID. Removing.")
                try:
                    self.lock_path.unlink()
                except OSError:
                    pass

        # 2. Acquire new lock
        try:
            with self.lock_path.open('w') as f:
                f.write(str(current_pid) + '\n')
            self._lock_acquired = True
            log.debug(f"Acquired lock for {self.resource_path} at PID {current_pid}.")
            # Ensure lock is released on normal program exit
            atexit.register(self.release)
        except OSError as e:
            raise RuntimeError(f"Failed to create lock file at {self.lock_path}: {e}")

    def release(self) -> None:
        """Release the lock file."""
        if self._lock_acquired and self.lock_path and self.lock_path.exists():
            try:
                self.lock_path.unlink()
                self._lock_acquired = False
                log.debug(f"Released lock at {self.lock_path}.")
                
                # Unregister the cleanup function
                # This must be done to prevent the lock from being released twice
                # (once manually, once at program exit)
                atexit.unregister(self.release)
            except OSError as e:
                log.error(f"Failed to remove lock file at {self.lock_path}: {e}")

    @staticmethod
    def _is_pid_running(pid: int) -> bool:
        """Check if a process with the given PID is currently running."""
        if pid <= 0:
            return False
        try:
            # The signal 0 check raises OSError if the PID does not exist.
            os.kill(pid, 0)
        except OSError as err:
            # Check for ESRCH (No such process)
            return err.errno != errno.ESRCH
        return True