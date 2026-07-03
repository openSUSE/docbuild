"""Load and process configuration files."""

from collections.abc import Iterable
from pathlib import Path
import tomllib as toml
from typing import Any

from .merge import deep_merge


def load_single_config(configfile: str | Path) -> dict[str, Any]:
    """Load a single TOML config file and return its content.

    :param configfile: Path to the config file.
    :return: The loaded config as a dictionary.
    :raise FileNotFoundError: If the config file does not exist.
    :raise tomllib.TOMLDecodeError: If the config file is not a valid TOML file
        or cannot be decoded.
    """
    with Path(configfile).open("rb") as f:
        return toml.load(f)


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
    """
    found_files: list[Path] = []
    found_configs: list[dict[str, Any]] = []

    # 1. Gather all existing config files
    if user_path:
        user_p = Path(user_path)
        found_files.append(user_p)
        # Preserve the original `user_path` type when loading to keep call-site behavior stable.
        found_configs.append(load_single_config(user_path))
    else:
        # Avoid string iteration bugs by safely determining the fallback tuple
        names_to_check = tuple(basenames) if basenames else ((default_filename,) if default_filename else ())

        # Search directories are expected to be ordered lowest-priority first
        for search_dir in search_dirs:
            for basename in names_to_check:
                candidate = Path(search_dir) / basename
                if candidate.exists():
                    found_files.append(candidate)
                    found_configs.append(load_single_config(candidate))
                    break  # Only take the highest priority basename per directory

    # 2. Check if we found anything at all
    if not found_files:
        return None, default_config, True

    # 3. Deep merge everything, starting with the defaults as the base!
    base = [default_config] if isinstance(default_config, dict) else []
    merged_config = deep_merge(*base, *found_configs)

    # 4. Return the merged config, but reverse the file list so the
    # highest-priority file is at index 0 for error reporting.
    return tuple(reversed(found_files)), merged_config, False
