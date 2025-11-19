"""Load and process configuration files."""

from collections.abc import Iterable, Sequence
from itertools import product
from pathlib import Path
import tomllib as toml
from typing import Any

from ..constants import DEFAULT_ENV_CONFIG_FILENAME
from .merge import deep_merge


# --- REMOVED THE OBSOLETE `process_envconfig` FUNCTION ---


def load_single_config(configfile: str | Path) -> dict[str, Any]:
    """Load a single TOML config file and return its content.

    :param configfile: Path to the config file.
    :return: The loaded config as a dictionary.
    :raise FileNotFoundError: If the config file does not exist.
    :raise tomllib.TOMLDecodeError: If the config file is not a valid TOML file
        or cannot be decoded.
    """
    with Path(configfile).open('rb') as f:
        return toml.load(f)


def load_and_merge_configs(
    defaults: Sequence[str | Path],
    *paths: str | Path,
) -> tuple[tuple[str | Path, ...], dict[str, Any]]:
    """Load config files and merge all content regardless of the nesting level.

    The order of defaults and paths is important. The paths are in the order of
    system path, user path, and current working directory.
    The defaults are in the order of common config file names followed by more
    specific ones. The later ones will override data from the earlier ones.

    :param defaults: a sequence of base filenames (without path!) to look for
                     in the paths
    :param paths: the paths to look for config files (without the filename!)
    :return: the found config files and the merged dictionary (raw dict)
    """
    configs: Sequence[dict[str, Any]] = []
    configfiles: Sequence[Path] = []

    # If no paths are provided, raise an error:
    if not paths:
        raise ValueError(
            'No paths provided. '
            'Please provide at least one path to load the config files.',
        )

    # Create a carthesian product of paths and default filenames:
    for path, cfgfile in product(paths, defaults):
        path = Path(path).expanduser().resolve() / cfgfile

        if path.exists():
            configfiles.append(path)
            configs.append(load_single_config(path))
        # Silently ignore files that do not exist:

    return tuple(configfiles), deep_merge(*configs)


def handle_config(
    user_path: Path | str | None,
    search_dirs: Iterable[str | Path],
    basenames: Iterable[str] | None,
    default_filename: str | None = None,
    default_config: object | None = None,
) -> tuple[tuple[Path, ...] | None, object | dict, bool]:
    """Return (config_files, config, from_defaults) for config file handling.

    Note: The returned configuration is the **raw loaded dictionary**. No
    placeholder replacement or validation has been performed on it.

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
    """
    if user_path:
        return (Path(user_path),), load_single_config(user_path), False

    for search_dir in search_dirs:
        if basenames:
            for basename in basenames:
                candidate = Path(search_dir) / basename
                if candidate.exists():
                    return (candidate,), load_single_config(candidate), False
        elif default_filename:
            candidate = Path(search_dir) / default_filename
            if candidate.exists():
                return (candidate,), load_single_config(candidate), False
    # Not found, use defaults
    return None, default_config, True