docbuild.logging
================

.. py:module:: docbuild.logging

.. autoapi-nested-parse::

   Set up logging for the documentation build process.



Attributes
----------

.. autoapisummary::

   docbuild.logging.LOGGERNAME
   docbuild.logging.LOGFILE
   docbuild.logging.KEEP_LOGS


Functions
---------

.. autoapisummary::

   docbuild.logging.create_base_log_dir
   docbuild.logging.setup_logging
   docbuild.logging.get_effective_level


Module Contents
---------------

.. py:data:: LOGGERNAME
   :value: 'docbuild'


   Name of the main logger for the application.


.. py:data:: LOGFILE
   :value: 'docbuild.log'


   Filename for the main log file.


.. py:data:: KEEP_LOGS
   :value: 4


   Number of log files to keep before rolling over.


.. py:function:: create_base_log_dir(base_log_dir: str | pathlib.Path = BASE_LOG_DIR) -> pathlib.Path

   Create the base log directory if it doesn't exist.

   This directory is typically located at :file:`~/.local/state/docbuild/logs`
   as per the XDG Base Directory Specification.

   :param base_log_dir: The base directory where logs should be stored.
       Considers the `XDG_STATE_HOME` environment variable if set.
   :return: The path to the base log directory.


.. py:function:: setup_logging(cliverbosity: int | None, fmt: str = '[%(levelname)s] %(funcName)s: %(message)s', logdir: str | pathlib.Path | None = None, default_logdir: str | pathlib.Path = BASE_LOG_DIR, use_queue: bool = True) -> None

   Set up logging for the application.

   :param cliverbosity: The verbosity level from the command line.
   :param fmt: The format string for log messages.
   :param logdir: The directory where log files should be stored.
   :param default_logdir: The default directory for logs.
   :param use_queue: Whether to use QueueHandler and QueueListener (for production).


.. py:function:: get_effective_level(verbosity: int | None, offset: int = 0) -> int

   Return a valid log level, clamped safely.

   :param verbosity: The verbosity level, typically from command
     line arguments (range 0..8)
   :param offset: An offset to apply to the verbosity level.
   :return: The effective log level.


