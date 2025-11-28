"""PID file locking utility."""

import errno
import fcntl
import io
import logging
import os
from pathlib import Path
from typing import ClassVar, Self, cast

from ..constants import BASE_LOCK_DIR

log = logging.getLogger(__name__)


# ------------------
# New Exception
# ------------------
class LockAcquisitionError(RuntimeError):
    """Raised when a process fails to acquire the PidFileLock because it is already held by another process."""
    pass


# ----------------------------------------
# Simplified PidFileLock Class
# ----------------------------------------
class PidFileLock:
    """Context manager for process-safe file locking using fcntl.

    Ensures only one process can hold a lock for a given resource.
    The mutual exclusion is guaranteed by the atomic fcntl.flock(LOCK_EX|LOCK_NB).
    The lock file is automatically created and is removed on successful exit.

    Implements a per-path singleton pattern: each lock_path has at most one instance within this process.
    """

    _instances: ClassVar[dict[Path, "PidFileLock"]] = {}

    def __new__(cls, resource_path: Path, lock_dir: Path = BASE_LOCK_DIR) -> Self:
        lock_path = cls._generate_lock_name(resource_path, lock_dir)
        if lock_path in cls._instances:
            return cast(Self, cls._instances[lock_path])

        instance = super().__new__(cls)
        cls._instances[lock_path] = instance
        return instance

    def __init__(self, resource_path: Path, lock_dir: Path = BASE_LOCK_DIR) -> None:
        # Prevent multiple initializations
        if hasattr(self, "_lock_path"):
            return

        self.resource_path = resource_path.resolve()
        self._lock_dir = lock_dir
        self._lock_path = self._generate_lock_name(resource_path, lock_dir)
        self._lock_acquired: bool = False
        self._handle: io.TextIOWrapper | None = None

    @property
    def lock_path(self) -> Path:
        return self._lock_path

    # --------------------
    # Core Locking Logic
    # --------------------

    def __enter__(self) -> Self:
        """Acquire the file lock using fcntl.flock(LOCK_EX | LOCK_NB)."""
        if self._lock_acquired:
            # Internal check for misuse, though public acquire is removed
            raise RuntimeError("Lock already acquired by this PidFileLock instance.")

        self._lock_dir.mkdir(parents=True, exist_ok=True)

        handle = None
        try:
            # 1. Open the file (creates it if needed)
            # Use os.open/os.fdopen for low-level file descriptor access needed by fcntl
            # fd = os.open(self._lock_path, os.O_RDWR | os.O_CREAT)
            # handle = os.fdopen(fd, "w+")
            handle = open(self._lock_path, 'w+')

            # 2. Acquire the exclusive, non-blocking fcntl lock. This is the atomic check.
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

            # 3. Write PID to the file (Optional, for debugging/identification)
            handle.seek(0)
            handle.truncate()
            handle.write(f"{os.getpid()}\n")
            handle.flush()

            self._handle = handle
            self._lock_acquired = True
            log.debug("Acquired fcntl lock for %s", self.resource_path)

        except OSError as e:
            # Check for non-blocking lock failure (EAGAIN/EWOULDBLOCK)
            if e.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
                # Clean up the file handle if we opened it but failed the lock
                if handle:
                    handle.close()
                # Raise the new, specific exception (Addressing reviewer point 3)
                raise LockAcquisitionError(
                    f"Resource is locked by another process (lock file {self._lock_path})"
                ) from e

            # Check for permission/access errors during file open (critical failure)
            elif e.errno in (errno.EACCES, errno.EPERM):
                 raise RuntimeError(f"Cannot acquire lock: {e}") from e

            # Re-raise other unexpected errors
            raise e

        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """Release the lock and remove the lock file."""
        if not self._lock_acquired or self._handle is None:
            return

        handle = self._handle

        # 1. Release the fcntl lock
        try:
            # Must use the file descriptor (handle.fileno()) for fcntl.flockq
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except OSError as e:
            # Log OS-level failures releasing the lock; don't raise from __exit__
            log.warning(
                "Failed to release fcntl lock for %s: %s", self.resource_path, e
            )

        # 2. Close the file handle
        try:
            handle.close()
        except (OSError, ValueError) as e:
            # Only handle known close-related errors (OS-level errors and ValueError
            # if the file object is in an invalid state). Allow other unexpected
            # exceptions to propagate.
            log.warning("Failed to close lock file handle %s: %s", self._lock_path, e)

        # 3. Remove the lock file
        try:
            self._lock_path.unlink(missing_ok=True)
            log.debug("Released fcntl lock and removed file %s", self._lock_path)
        except OSError as e:
            # Only catch OS-level errors from unlink (e.g. permission issues);
            # allow other unexpected exceptions to propagate.
            log.warning(f"Failed to remove lock file {self._lock_path}: {e}")

        self._handle = None
        self._lock_acquired = False

    @staticmethod
    def _generate_lock_name(resource_path: Path, lock_dir: Path) -> Path:
        import hashlib

        path_hash = hashlib.sha256(str(resource_path.resolve()).encode("utf-8")).hexdigest()
        return Path(lock_dir) / f"docbuild-{path_hash}.pid"
