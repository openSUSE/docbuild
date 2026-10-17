"""PID file locking utility.

Provides a context-manager-based process-safe lock using fcntl to ensure
only one process can hold a lock for a given resource path. The lock file
is created automatically and removed on exit.
"""

import errno
import fcntl
import io
import logging
import os
from pathlib import Path
from typing import ClassVar, Self, cast

from ..constants import BASE_LOCK_DIR

log = logging.getLogger(__name__)


class LockAcquisitionError(RuntimeError):
    """Raised when a file lock cannot be acquired because it is already held.

    This exception indicates that another process currently holds the exclusive
    lock on the resource.
    """

    pass


class PidFileLock:
    """Context manager for process-safe file locking using fcntl.

    Ensures only one process can hold a lock for a given resource.
    The mutual exclusion is guaranteed by the atomic fcntl.flock(LOCK_EX|LOCK_NB).
    The lock file is automatically created and is removed on successful exit.

    Implements a per-path singleton pattern: each lock_path has at most one
    instance within this process.

    .. code-block:: python

        from pathlib import Path
        from docbuild.utils.pidlock import PidFileLock

        resource = Path("/tmp/my-resource")
        try:
            with PidFileLock(resource) as lock:
                # critical section
                print("Lock acquired at", lock.lock_path)
        except LockAcquisitionError:
            print("Resource is already locked by another process")
    """

    _instances: ClassVar[dict[Path, "PidFileLock"]] = {}

    def __new__(cls, resource_path: Path, lock_dir: Path = BASE_LOCK_DIR) -> Self:
        """Implement per-path singleton behavior.

        :param resource_path: The path of the resource to lock.
        :param lock_dir: Directory in which lock files are stored.
            Defaults to :data:`BASE_LOCK_DIR`.
        :return: The singleton instance for the derived lock path.
        """
        lock_path = cls._generate_lock_name(resource_path, lock_dir)
        if lock_path in cls._instances:
            return cast(Self, cls._instances[lock_path])

        instance = super().__new__(cls)
        cls._instances[lock_path] = instance
        return instance

    def __init__(self, resource_path: Path, lock_dir: Path = BASE_LOCK_DIR) -> None:
        """Initialize the lock for a resource path.

        Subsequent calls for the same path return the existing instance
        without re-initialization.

        :param resource_path: The path of the resource to lock.
        :param lock_dir: Directory in which lock files are stored.
        """
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
        """Get the path to the lock file.

        :return: Absolute path of the lock file for this resource.
        """
        return self._lock_path

    def __enter__(self) -> Self:
        """Acquire the exclusive, non-blocking file lock.

        Creates the lock directory and lock file if necessary, then attempts
        to acquire an exclusive lock via :func:`~fcntl.flock`. Writes the current
        process PID into the lock file for debugging.

        :return: Self, so the lock can be used as a context manager.
        :raises LockAcquisitionError: If another process already holds the lock.
        :raises RuntimeError: If the lock is already acquired by this instance
            or if a permission error occurs.
        """
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
            handle = open(self._lock_path, "w+")

            # 2. Acquire the exclusive, non-blocking fcntl lock.
            # This is the atomic check.
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
                    "Resource is locked by another process "
                    f"(lock file {self._lock_path})"
                ) from e

            # Check for permission/access errors during file open (critical failure)
            elif e.errno in (errno.EACCES, errno.EPERM):
                raise RuntimeError(f"Cannot acquire lock: {e}") from e

            # Re-raise other unexpected errors
            raise e

        return self

    def __exit__(self,
                 exc_type: type[BaseException] | None,
                 exc_value: BaseException | None,
                 traceback: object | None) -> None:
        """Release the lock and remove the lock file.

        Releases the fcntl lock, closes the file handle, and deletes the
        lock file. Failures during release are logged but do not raise
        exceptions (to avoid masking the original exception).

        :param exc_type: Exception type if an exception occurred, else None.
        :param exc_value: Exception instance if an exception occurred, else None.
        :param traceback: Traceback object if an exception occurred, else None.
        """
        if not self._lock_acquired or self._handle is None:
            return

        handle = self._handle

        # 1. Release the fcntl lock
        try:
            # Must use the file descriptor (handle.fileno()) for fcntl.flock
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
        """Generate a deterministic lock file path from a resource path.

        Uses a SHA-256 hash of the resolved resource path so that different
        resources produce distinct lock files within ``lock_dir``.

        :param resource_path: The resource whose lock file name is derived.
        :param lock_dir: Directory in which the lock file will be placed.
        :return: Path of the lock file (``lock_dir / docbuild-<hash>.pid``).
        """
        import hashlib

        path_hash = hashlib.sha256(
            str(resource_path.resolve()).encode("utf-8")
        ).hexdigest()
        return Path(lock_dir) / f"docbuild-{path_hash}.pid"
