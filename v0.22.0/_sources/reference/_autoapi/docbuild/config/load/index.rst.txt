docbuild.config.load
====================

.. py:module:: docbuild.config.load

.. autoapi-nested-parse::

   Load and process configuration files.



Functions
---------

.. autoapisummary::

   docbuild.config.load.load_single_config
   docbuild.config.load.handle_config


Module Contents
---------------

.. py:function:: load_single_config(configfile: str | pathlib.Path) -> dict[str, Any]

   Load a single TOML config file and return its content.

   :param configfile: Path to the config file.
   :return: The loaded config as a dictionary.
   :raise FileNotFoundError: If the config file does not exist.
   :raise tomllib.TOMLDecodeError: If the config file is not a valid TOML file
       or cannot be decoded.


.. py:function:: handle_config(user_path: pathlib.Path | str | None, search_dirs: collections.abc.Iterable[str | pathlib.Path], basenames: collections.abc.Iterable[str] | None, default_filename: str | None = None, default_config: object | None = None) -> tuple[tuple[pathlib.Path, Ellipsis] | None, object | dict, bool]

   Return (config_files, config, from_defaults) for config file handling.

   Note: The returned configuration is the **raw loaded dictionary**. No
   placeholder replacement or validation has been performed on it.
   Configurations are collected across all search directories and deeply merged
   on top of the default configuration to allow partial user configs.

   :param user_path: Path to the user-defined config file, if any.
   :param search_dirs: Iterable of directories to search for config files.
   :param basenames: Iterable of base filenames to search for.
   :param default_filename: Default filename to use if no config file is found.
   :param default_config: Default configuration to return if no config file is found.
   :return: A tuple containing:

       * A tuple of found config file paths or None if no config file is found.
       * The loaded configuration as a dictionary or the default configuration.
       * A boolean indicating if the default configuration was used exclusively.


