docbuild.utils.contextmgr.PersistentOnErrorTemporaryDirectory
=============================================================

.. py:class:: docbuild.utils.contextmgr.PersistentOnErrorTemporaryDirectory(suffix: str | None = None, prefix: str | None = None, dir: str | pathlib.Path | None = None)

   Bases: :py:obj:`tempfile.TemporaryDirectory`

   .. autoapi-inheritance-diagram:: docbuild.utils.contextmgr.PersistentOnErrorTemporaryDirectory
      :parts: 1


   A temporary directory that supports both sync and async usage.

   It deletes the temporary directory only if no exception occurs within the
   context block. This is useful for debugging, as it preserves the directory
   and its contents for inspection after an error.

   It is a subclass of :class:`tempfile.TemporaryDirectory` and mimics its
   initializer.

   .. code-block:: python

       # Synchronous usage
       with PersistentOnErrorTemporaryDirectory() as temp_dir:
           # temp_dir is a Path object
           ...

       # Asynchronous usage
       async with PersistentOnErrorTemporaryDirectory() as temp_dir:
           # temp_dir is a Path object
           ...

   Optional arguments:
   :param suffix: A str suffix for the directory name.  (see mkdtemp)
   :param prefix: A str prefix for the directory name.  (see mkdtemp)
   :param dir: A directory to create this temp dir in.  (see mkdtemp)


   .. py:method:: __enter__() -> pathlib.Path

      Enter the runtime context and create the temporary directory.

      :returns: Path to the created temporary directory.



   .. py:method:: __aenter__() -> pathlib.Path
      :async:


      Enter the async runtime context and create the temporary directory.

      :returns: Path to the created temporary directory.



   .. py:method:: __exit__(exc_type: ExcType, exc_val: ExcVal, exc_tb: ExcTback) -> None

      Exit the runtime context and delete the directory if no exception occurred.

      :param exc_type: Exception type, if any.
      :param exc_val: Exception instance, if any.
      :param exc_tb: Traceback, if any.



   .. py:method:: __aexit__(exc_type: ExcType, exc_val: ExcVal, exc_tb: ExcTback) -> None
      :async:


      Asynchronously clean up the directory on successful exit.

      Async exit the runtime context and delete the directory if no
      exception occurred.

      :param exc_type: Exception type, if any.
      :param exc_val: Exception instance, if any.
      :param exc_tb: Traceback, if any.


