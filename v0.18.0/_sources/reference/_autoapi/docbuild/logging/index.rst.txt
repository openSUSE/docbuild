docbuild.logging
================

.. py:module:: docbuild.logging

.. autoapi-nested-parse::

   Set up logging for the documentation build process.



Functions
---------

.. autoapisummary::

   docbuild.logging.register_background_thread
   docbuild.logging.create_base_log_dir
   docbuild.logging.build_handlers_from_config
   docbuild.logging.setup_logging


Module Contents
---------------

.. py:function:: register_background_thread(thread: threading.Thread) -> None

   Register a thread to be joined on logging shutdown.


.. py:function:: create_base_log_dir(base_log_dir: str | pathlib.Path = BASE_LOG_DIR) -> pathlib.Path

   Create the base log directory if it doesn't exist.


.. py:function:: build_handlers_from_config(config: dict[str, Any]) -> list[logging.Handler]

   Build handler instances from a logging config dict without starting listeners.

   This is a small helper useful for unit tests: it constructs handler
   objects and attaches formatters according to the provided `config`
   but does not start any background listener or register global state.


.. py:function:: setup_logging(cliverbosity: int, user_config: dict[str, Any] | None = None) -> None

   Set up a non-blocking, configurable logging system.


