docbuild.config.load
====================

.. py:module:: docbuild.config.load

.. autoapi-nested-parse::

   Load and process configuration files.



Functions
---------

.. autoapisummary::

   docbuild.config.load.process_envconfig
   docbuild.config.load.load_single_config
   docbuild.config.load.load_and_merge_configs
   docbuild.config.load.handle_config


Module Contents
---------------

.. py:function:: process_envconfig(envconfigfile: str | pathlib.Path | None) -> tuple[pathlib.Path, dict[str, Any]]

   Process the env config.

   :param envconfigfile: Path to the env TOML config file.
   :return: Tuple of the env config file path and the config object.
   :raise ValueError: If neither envconfigfile nor role is provided.


.. py:function:: load_single_config(configfile: str | pathlib.Path) -> dict[str, Any]

   Load a single TOML config file and return its content.

   :param configfile: Path to the config file.
   :return: The loaded config as a dictionary.
   :raise FileNotFoundError: If the config file does not exist.
   :raise tomllib.TOMLDecodeError: If the config file is not a valid TOML file
       or cannot be decoded.


.. py:function:: load_and_merge_configs(defaults: collections.abc.Sequence[str | pathlib.Path], *paths: str | pathlib.Path) -> tuple[tuple[str | pathlib.Path, Ellipsis], dict[str, Any]]

   Load config files and merge all content regardless of the nesting level.

   The order of defaults and paths is important. The paths are in the order of
   system path, user path, and current working directory.
   The defaults are in the order of common config file names followed by more
   specific ones. The later ones will override data from the earlier ones.

   :param defaults: a sequence of base filenames (without path!) to look for
                    in the paths
   :param paths: the paths to look for config files (without the filename!)
   :return: the found config files and the merged dictionary


.. py:function:: handle_config(user_path: pathlib.Path | str | None, search_dirs: collections.abc.Iterable[str | pathlib.Path], basenames: collections.abc.Iterable[str] | None, default_filename: str | None = None, default_config: object | None = None) -> tuple[tuple[pathlib.Path, Ellipsis] | None, object | dict, bool]

   Return (config_files, config, from_defaults) for config file handling.

   :param user_path: Path to the user-defined config file, if any.
   :param search_dirs: Iterable of directories to search for config files.
   :param basenames: Iterable of base filenames to search for.
   :param default_filename: Default filename to use if no config file is found.
   :param default_config: Default configuration to return if no config file is found.
   :return: A tuple containing:

       * A tuple of found config file paths or None if no config file is found.
       * The loaded configuration as a dictionary or the default configuration.
       * A boolean indicating if the default configuration was used.
   :raises ValueError: If no config file is found and no default
       configuration is provided.


