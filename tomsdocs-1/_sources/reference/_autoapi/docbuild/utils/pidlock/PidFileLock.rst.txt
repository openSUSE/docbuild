docbuild.utils.pidlock.PidFileLock
==================================

.. py:class:: docbuild.utils.pidlock.PidFileLock(resource_path: pathlib.Path, lock_dir: pathlib.Path = BASE_LOCK_DIR)

   Context manager for process-safe file locking using fcntl.

   Ensures only one process can hold a lock for a given resource.
   The mutual exclusion is guaranteed by the atomic fcntl.flock(LOCK_EX|LOCK_NB).
   The lock file is automatically created and is removed on successful exit.

   Implements a per-path singleton pattern: each lock_path has at most one
   instance within this process.


   .. py:property:: lock_path
      :type: pathlib.Path


      Get the path to the lock file.



   .. py:method:: __enter__() -> Self

      Acquire the file lock using fcntl.flock(LOCK_EX | LOCK_NB).



   .. py:method:: __exit__(exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: object | None) -> None

      Release the lock and remove the lock file.


