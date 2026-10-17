"""Tests for :mod:`docbuild.constants`."""

from pathlib import Path

from docbuild.constants import (
    CONFIG_PATHS,
    SYSTEM_CONFIG_DIR,
    _xdg_site_config_dirs,
)


def test_xdg_site_config_dirs_default(monkeypatch):
    """Without XDG_CONFIG_DIRS set, platformdirs falls back to its default."""
    monkeypatch.delenv("XDG_CONFIG_DIRS", raising=False)
    dirs = _xdg_site_config_dirs("docbuild")
    assert len(dirs) == 1
    assert all(isinstance(path, Path) for path in dirs)


def test_xdg_site_config_dirs_multiple(monkeypatch):
    """Multiple XDG_CONFIG_DIRS entries are split into separate Paths."""
    monkeypatch.setenv("XDG_CONFIG_DIRS", "/etc/xdg:/opt/etc/xdg")
    dirs = _xdg_site_config_dirs("docbuild")
    assert dirs == (Path("/etc/xdg/docbuild"), Path("/opt/etc/xdg/docbuild"))


def test_config_paths_includes_xdg_and_system_dir():
    """CONFIG_PATHS keeps the fixed system dir and includes XDG dirs before it."""
    assert SYSTEM_CONFIG_DIR in CONFIG_PATHS
    system_idx = CONFIG_PATHS.index(SYSTEM_CONFIG_DIR)
    # Everything before SYSTEM_CONFIG_DIR must be an XDG config dir.
    assert all(
        str(path).replace("\\", "/").endswith("docbuild")
        for path in CONFIG_PATHS[:system_idx]
    )
