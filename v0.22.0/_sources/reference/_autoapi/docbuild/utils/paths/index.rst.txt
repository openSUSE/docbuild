docbuild.utils.paths
====================

.. py:module:: docbuild.utils.paths

.. autoapi-nested-parse::

   Module for Path related utilities.



Functions
---------

.. autoapisummary::

   docbuild.utils.paths.calc_max_len
   docbuild.utils.paths.mark_cache_dir


Module Contents
---------------

.. py:function:: calc_max_len(files: tuple[pathlib.Path | str, Ellipsis], last_parts: int = -2) -> int

   Calculate the maximum length of file names.

   Shortens the filenames to the last parts of the path (last_parts)
   for display purposes, ensuring the maximum length is even.

   :param files: A tuple of file paths to calculate lengths for.
   :param last_parts: Number of parts from the end of the path to consider.
      Needs to be negative to count from the end.
      By default, it considers the last two parts.
   :return: The maximum length of the shortened file names.

   .. code-block:: python

       >>> files = (Path('/path/to/file1.xml'), Path('/another/path/to/file2.xml'))
       >>> calc_max_len(files)
       30


.. py:function:: mark_cache_dir(path: pathlib.Path | str) -> None

   Add a standard CACHEDIR.TAG file to a directory.

   This tag informs backup tools that the directory contains cached data
   that can be safely excluded from backups. The directory is created if
   it does not exist.

   For more information, see: https://bford.info/cachedir/


