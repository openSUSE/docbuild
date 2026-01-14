docbuild.utils.contextmgr
=========================

.. py:module:: docbuild.utils.contextmgr

.. autoapi-nested-parse::

   Provides context managers.



Classes
-------

.. toctree::
   :hidden:

   /reference/_autoapi/docbuild/utils/contextmgr/TimerData
   /reference/_autoapi/docbuild/utils/contextmgr/PersistentOnErrorTemporaryDirectory

.. autoapisummary::

   docbuild.utils.contextmgr.TimerData
   docbuild.utils.contextmgr.PersistentOnErrorTemporaryDirectory


Functions
---------

.. autoapisummary::

   docbuild.utils.contextmgr.make_timer
   docbuild.utils.contextmgr.edit_json


Module Contents
---------------

.. py:function:: make_timer(name: str, method: collections.abc.Callable[[], float] = time.perf_counter) -> collections.abc.Callable[[], contextlib.AbstractContextManager[TimerData]]

   Create independent context managers to measure elapsed time.

   Each timer is independent and can be used in a context manager.
   The name is used to identify the timer.

   :param name: Name of the timer.
   :param method: A callable that returns a float, used for measuring time.
       Defaults to :func:`time.perf_counter`.
   :return: A callable that returns a context manager. The context manager
       yields a :class:`TimerData` object.

   .. code-block:: python

       timer = make_timer('example_timer')

       with timer() as timer_data:
           # Code to be timed
           pass

       timer_data.elapsed  # Access the elapsed time


.. py:function:: edit_json(path: pathlib.Path | str) -> collections.abc.Iterator[dict[str, Any]]

   Context manager for safely and atomically editing a JSON file.

   This function implements a "read-modify-write" cycle with ACID-like properties.
   It ensures that the file is either fully updated or remains strictly unchanged
   (no partial writes or corruption) if an error occurs during modification or saving.

   The operation follows three phases:

   1. **Read**: The file is parsed into a Python dictionary.
   2. **Modify** (Yield): Control is handed to the caller to modify the dictionary.
   3. **Write**:
      - If the block exits successfully, the data is written to a temporary file,
        fsync-ed to disk, and atomically renamed over the original file.
      - If an exception is raised within the block, the write phase is skipped
        entirely.

   :param path: The path to the JSON file to edit.
   :yields: The content of the JSON file as a mutable dictionary.

   :raises FileNotFoundError: If the specified ``path`` does not exist.
   :raises json.JSONDecodeError: If the file exists but contains invalid JSON.
   :raises OSError: If an I/O error occurs during reading, writing, or fsyncing.

   Example usage:

   .. code-block:: python

       with edit_json('config.json') as data:
           config["docs"][0]["dcfile"] = path.name
           config["docs"][0]["format"]["html"] = "..."
           # more modifications...


