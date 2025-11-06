import errno
import fcntl
import io
import logging
import os
from pathlib import Path
from typing import Optional, Self

from ..constants import BASE_LOCK_DIR

log = logging.getLogger(__name__)


class PidFileLock:
    def __init__(self, resource_path: Path, lock_dir: Path = BASE_LOCK_DIR) -> None:
        self.resource_path = resource_path.resolve()
        self._lock_dir = lock_dir
        self._lock_path = self._generate_lock_name()
        self._lock_acquired: bool = False
        self._handle: Optional[io.TextIOWrapper] = None

    @property
    def lock_dir(self) -> Path:
        return self._lock_dir

    @property
    def lock_path(self) -> Path:
        return self._lock_path

    @property
    def lock(self) -> bool:
        return self._lock_acquired

    @property
    def lock_file(self):
        return getattr(self, "_handle", None)

    def __enter__(self) -> Self:
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.release()

    def _generate_lock_name(self) -> Path:
        import hashlib

        path_hash = hashlib.sha256(str(self.resource_path).encode("utf-8")).hexdigest()
        return self._lock_dir / f"docbuild-{path_hash}.pid"

    def acquire(self) -> None:
        if self._lock_acquired:
            raise RuntimeError("Lock already acquired")

        self._lock_dir.mkdir(parents=True, exist_ok=True)

        # Check for existing lock file
        if self._lock_path.exists():
            try:
                with self._lock_path.open("r") as f:
                    try:
                        pid = int(f.read().strip())
                        try:
                            os.kill(pid, 0)
                            raise RuntimeError(
                                f"Resource is locked by PID {pid} (file {self._lock_path})"
                            )
                        except ProcessLookupError:
                            self._lock_path.unlink()
                        except PermissionError:
                            log.error("Non-critical error while checking lock file: permission denied")
                        except OSError as e:
                            log.error(f"Non-critical error while checking lock file: {e}")
                    except ValueError:
                        log.error(f"Invalid PID in lock file {self._lock_path}, removing")
                        try:
                            self._lock_path.unlink()
                        except OSError:
                            pass
            except OSError as e:
                log.error(f"Non-critical error while reading lock file: {e}")
                try:
                    self._lock_path.unlink()
                except OSError:
                    pass

        # Save the real os.open to prevent recursion in tests
        _real_os_open = os.open

        # Acquire the lock safely
        try:
            fd = _real_os_open(self._lock_path, os.O_RDWR | os.O_CREAT)
            handle = os.fdopen(fd, "w+")
        except OSError as e:
            if e.errno in (errno.EACCES, errno.EPERM):
                raise RuntimeError(f"Cannot acquire lock: {e}") from e
            else:
                log.error(f"Non-critical error while opening lock file: {e}")
                # Fallback attempt
                fd = _real_os_open(self._lock_path, os.O_RDWR | os.O_CREAT)
                handle = os.fdopen(fd, "w+")

        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as e:
            handle.close()
            raise RuntimeError(f"docbuild instance already running (lock {self._lock_path}): {e}") from e

        try:
            handle.seek(0)
            handle.truncate()
            handle.write(f"{os.getpid()}\n")
            handle.flush()
        except OSError as e:
            log.warning(f"Failed to write PID to lock file: {e}")

        self._handle = handle
        self._lock_acquired = True
        log.debug("Acquired fcntl lock for %s", self.resource_path)

    def release(self) -> None:
        if not self._lock_acquired or self._handle is None:
            return

        try:
            fcntl.flock(self._handle, fcntl.LOCK_UN)
        except Exception:
            pass

        try:
            self._handle.close()
        except Exception:
            pass

        self._handle = None
        self._lock_acquired = False

        try:
            self._lock_path.unlink(missing_ok=True)
        except Exception:
            log.warning(f"Failed to remove lock file {self._lock_path}")

        log.debug("Released fcntl lock %s", self._lock_path)
