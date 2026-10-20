"""Tests for :mod:`docbuild.constants`."""

from pathlib import Path

from docbuild.constants import (
    CONFIG_PATHS,
    SYSTEM_CONFIG_DIR,
    XDG_CONFIG_DIRS_PATHS,
    xdg_site_config_dirs,
)


def test_xdg_site_config_dirs_default(monkeypatch):
    """Without XDG_CONFIG_DIRS set, platformdirs falls back to its default."""
    monkeypatch.delenv("XDG_CONFIG_DIRS", raising=False)
    dirs = xdg_site_config_dirs("docbuild")
    assert len(dirs) == 1
    assert all(isinstance(path, Path) for path in dirs)


def test_xdg_site_config_dirs_multiple(monkeypatch):
    """Multiple XDG_CONFIG_DIRS entries are split into separate Paths."""
    monkeypatch.setenv("XDG_CONFIG_DIRS", "/etc/xdg:/opt/etc/xdg")
    dirs = xdg_site_config_dirs("docbuild")
    assert dirs == (Path("/etc/xdg/docbuild"), Path("/opt/etc/xdg/docbuild"))


def test_xdg_site_config_dirs_deduplicates(monkeypatch):
    """Duplicate and empty XDG_CONFIG_DIRS entries are dropped, order is kept."""
    monkeypatch.setenv("XDG_CONFIG_DIRS", "/a::/b:/a")
    dirs = xdg_site_config_dirs("docbuild")
    assert dirs == (Path("/a/docbuild"), Path("/b/docbuild"))


def test_config_paths_includes_xdg_and_system_dir():
    """CONFIG_PATHS puts XDG dirs (lowest priority first) before the system dir."""
    assert SYSTEM_CONFIG_DIR in CONFIG_PATHS
    system_idx = CONFIG_PATHS.index(SYSTEM_CONFIG_DIR)
    # Everything before SYSTEM_CONFIG_DIR must be an XDG config dir.
    assert system_idx > 0
    assert CONFIG_PATHS[:system_idx] == tuple(reversed(XDG_CONFIG_DIRS_PATHS))
