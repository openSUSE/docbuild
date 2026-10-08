docbuild.utils.errors
=====================

.. py:module:: docbuild.utils.errors

.. autoapi-nested-parse::

   Utilities for handling and formatting application errors.



Functions
---------

.. autoapisummary::

   docbuild.utils.errors.format_pydantic_error
   docbuild.utils.errors.format_toml_error


Module Contents
---------------

.. py:function:: format_pydantic_error(error: pydantic.ValidationError, model_class: type[pydantic.BaseModel], config_file: str, verbose: int = 0, console: rich.console.Console | None = None) -> None

   Centralized formatter for Pydantic ValidationErrors using Rich.

   :param error: The caught ValidationError object.
   :param model_class: The Pydantic model class that failed validation.
   :param config_file: The name/path of the config file being processed.
   :param verbose: Verbosity level to control error detail.
   :param console: Optional Rich console object. If None, creates a stderr console.


.. py:function:: format_toml_error(error: tomllib.TOMLDecodeError, config_file: str, console: rich.console.Console | None = None) -> None

   Format TOML syntax errors using Rich.

   :param error: The caught TOMLDecodeError object.
   :param config_file: The name/path of the config file with the syntax error.
   :param console: Optional Rich console object.


