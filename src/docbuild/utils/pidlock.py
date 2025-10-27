"""PID file locking utility."""

import atexit
import hashlib
import logging
import os
import errno
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
        
        # Converted public attributes to private attributes
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
        self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: Any
    ) -> None:
        """Release the lock."""
        self.release()

    def _generate_lock_name(self) -> Path:
        """Generate a unique lock file name based on the resource path."""
        # SHA256 hash of the absolute path is used to ensure a unique, safe filename.
        path_hash = hashlib.sha256(str(self.resource_path).encode('utf-8')).hexdigest()
        return self._lock_dir / f'docbuild-{path_hash}.pid'

    def acquire(self) -> None:
        """Acquire the lock atomically, or diagnose an existing lock."""
        self.lock_dir.mkdir(parents=True, exist_ok=True)
        current_pid = os.getpid()

        # 1. Attempt to acquire the lock file atomically (O_CREAT | os.O_EXCL)
        try:
            # os.O_WRONLY | os.O_CREAT | os.O_EXCL ensures file is created ONLY if it doesn't exist.
            # 0o644 sets the file permissions (read/write for owner, read for others).
            lock_fd = os.open(
                self.lock_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644
            )
            # Write PID to the atomically created file
            with os.fdopen(lock_fd, 'w') as f:
                f.write(str(current_pid) + '\n')

            self._lock_acquired = True
            log.debug(f"Acquired lock for {self.resource_path} at PID {current_pid}.")
            # Registering release ensures the lock is cleaned up when the program exits.
            atexit.register(self.release)
            return

        except FileExistsError:
            # 2. Lock file exists (atomic open failed). Must now check if it's stale or running.
            pass
        except OSError as e:
            # Catch file system errors during the atomic open operation
            raise RuntimeError(f"Failed to create lock file at {self.lock_path}: {e}")

        # 3. Lock exists. Check if the process is running.
        if self.lock_path.exists():
            try:
                # Read PID from the file content (slower operation, only done on contention)
                with self.lock_path.open('r') as f:
                    pid_str = f.read().strip()
                
                pid = int(pid_str)
                
                # Check if the process is actually running
                if self._is_pid_running(pid):
                    # Running instance found. Raise the error.
                    raise RuntimeError(
                        f"docbuild instance already running (PID: {pid}) "
                        f"for configuration: {self.resource_path}"
                    )
                else:
                    # Stale lock. Attempt to clean up and acquire again.
                    log.warning(
                        f"Found stale lock file at {self.lock_path} (PID {pid}). Removing and retrying acquisition."
                    )
                    self.lock_path.unlink()
                    
                    # Recursively call acquire() to try and grab the lock immediately.
                    return self.acquire() 

            except FileNotFoundError:
                # Race condition: another process removed the stale lock before us. Retry.
                return self.acquire() 
            except ValueError:
                # Invalid PID format. Treat as stale and clean up.
                log.warning(f"Lock file at {self.lock_path} contains invalid PID. Removing and retrying.")
                self.lock_path.unlink()
                return self.acquire()
            except OSError as e:
                # Non-critical I/O error during read/unlink attempt
                log.error(f"Non-critical error while checking lock file: {e}")
            
        # If all checks and retries fail to acquire the lock, raise a final error.
        raise RuntimeError(f"Failed to acquire lock for {self.resource_path} after multiple checks.")

    def release(self) -> None:
        """Release the lock file."""
        if self._lock_acquired and self.lock_path.exists():
            try:
                self.lock_path.unlink()
                self._lock_acquired = False
                log.debug("Released lock at %s.", self.lock_path)
                
                # Unregister the cleanup function
                atexit.unregister(self.release)
            except OSError as e:
                log.error(f"Failed to remove lock file at {self.lock_path}: {e}")

    @staticmethod
    def _is_pid_running(pid: int) -> bool:
        """Check if a process with the given PID is currently running.
        
        :param pid: The PID to check
        :return: True, if the process with the given PID is running,
                 False otherwise
        """
        if pid <= 0:
            return False
        try:
            # Sending signal 0 will raise an OSError exception if the pid is
            # not running. Do nothing otherwise.
            os.kill(pid, 0)
            return True
        except OSError as err:
            # Check for ESRCH (No such process)
            return err.errno != errno.ESRCH