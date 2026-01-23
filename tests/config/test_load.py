from pathlib import Path
import tempfile
from typing import Any

import docbuild.config.load as load_mod
from docbuild.config.load import handle_config

# Define a placeholder for the expected Container type for clarity in tests
Container = dict[str, Any]


def test_handle_config_user_path(monkeypatch):
    config_file = Path("/fake/path/myconfig.toml")
    called = {}

    def fake_load_single_config(path):
        called["path"] = path
        return {"section": {"key": "value"}}

    monkeypatch.setattr(load_mod, "load_single_config", fake_load_single_config)
    result = handle_config(config_file, [], None, None, None)
    assert result[0] == (config_file,)
    assert result[1] == {"section": {"key": "value"}}
    assert result[2] is False
    assert called["path"] == config_file


def test_handle_config_user_path_str(monkeypatch):
    # Accepts a string as user_path
    config_file = "/fake/path/myconfig.toml"
    called = {}

    def fake_load_single_config(path):
        called["path"] = path
        return {"section": {"key": "value"}}

    monkeypatch.setattr(load_mod, "load_single_config", fake_load_single_config)
    result = handle_config(config_file, [], None, None, None)
    # Should convert to Path
    assert result[0] == (Path(config_file),)
    assert result[1] == {"section": {"key": "value"}}
    assert result[2] is False
    assert called["path"] == config_file


def test_handle_config_search_dirs_and_basenames(monkeypatch):
    search_dir = Path("/fake/dir")
    basename = "found.toml"
    config_file = search_dir / basename

    def fake_exists(self):
        return self == config_file

    monkeypatch.setattr(Path, "exists", fake_exists)

    def fake_load_single_config(path):
        return {"section": {"key": "found"}}

    monkeypatch.setattr(load_mod, "load_single_config", fake_load_single_config)
    result = handle_config(None, [search_dir], [basename], None, None)
    assert result[0] == (config_file,)
    assert result[1] == {"section": {"key": "found"}}
    assert result[2] is False


def test_handle_config_basename_and_default_filename(monkeypatch):
    # Both basenames and default_filename are given, only basenames should be used
    search_dir = Path("/fake/dir")
    basename = "found.toml"
    default_filename = "default.toml"
    config_file = search_dir / basename

    def fake_exists(self):
        return self == config_file

    monkeypatch.setattr(Path, "exists", fake_exists)

    def fake_load_single_config(path):
        return {"section": {"key": "found"}}

    monkeypatch.setattr(load_mod, "load_single_config", fake_load_single_config)
    # default_filename should be ignored if basenames is not None
    result = handle_config(None, [search_dir], [basename], default_filename, None)
    assert result[0] == (config_file,)
    assert result[1] == {"section": {"key": "found"}}
    assert result[2] is False


def test_handle_config_search_dirs_and_default_filename(monkeypatch):
    search_dir = Path("/fake/dir")
    default_filename = "default.toml"
    config_file = search_dir / default_filename

    def fake_exists(self):
        return self == config_file

    monkeypatch.setattr(Path, "exists", fake_exists)

    def fake_load_single_config(path):
        return {"section": {"key": "default"}}

    monkeypatch.setattr(load_mod, "load_single_config", fake_load_single_config)
    result = handle_config(None, [search_dir], None, default_filename, None)
    assert result[0] == (config_file,)
    assert result[1] == {"section": {"key": "default"}}
    assert result[2] is False


def test_handle_config_empty_search_dirs(monkeypatch):
    # If search_dirs is empty, should return default
    default = {"default": True}
    result = handle_config(None, [], ["nope.toml"], None, default)
    assert result[0] is None
    assert result[1] == default
    assert result[2] is True


def test_handle_config_empty_basenames_and_default_filename(monkeypatch):
    # If both basenames and default_filename are None, should return default
    default = {"default": True}
    result = handle_config(None, [Path("/any")], None, None, default)
    assert result[0] is None
    assert result[1] == default
    assert result[2] is True


def test_handle_config_not_found_returns_default(monkeypatch):
    # Patch Path.exists to always return False
    monkeypatch.setattr(Path, "exists", lambda self: False)
    default = {"default": True}
    result = handle_config(None, [Path("/nonexistent")], ["nope.toml"], None, default)
    assert result[0] is None
    assert result[1] == default
    assert result[2] is True


def test_handle_config_multiple_basenames_one_exists(monkeypatch):
    search_dir = Path("/fake/dir")
    basenames = ["notfound.toml", "found.toml"]
    found_file = search_dir / basenames[1]

    # Patch Path.exists: only found_file returns True
    def fake_exists(self):
        return self == found_file

    monkeypatch.setattr(Path, "exists", fake_exists)

    def fake_load_single_config(path):
        return {"section": {"key": "found"}}

    monkeypatch.setattr(load_mod, "load_single_config", fake_load_single_config)
    result = handle_config(None, [search_dir], basenames, None, None)
    assert result[0] == (found_file,)
    assert result[1] == {"section": {"key": "found"}}
    assert result[2] is False


def test_handle_config_first_basename_exists(monkeypatch):
    search_dir = Path("/fake/dir")
    basenames = ["first.toml", "second.toml"]
    first_file = search_dir / basenames[0]

    # Patch Path.exists: only first_file returns True
    def fake_exists(self):
        return self == first_file

    monkeypatch.setattr(Path, "exists", fake_exists)

    def fake_load_single_config(path):
        return {"section": {"key": "first"}}

    monkeypatch.setattr(load_mod, "load_single_config", fake_load_single_config)
    result = handle_config(None, [search_dir], basenames, None, None)
    assert result[0] == (first_file,)
    assert result[1] == {"section": {"key": "first"}}
    assert result[2] is False


def test_handle_config_falls_back_to_default_with_default_filename(tmp_path):
    """Test fallback to default config when using default_filename."""
    with tempfile.TemporaryDirectory(dir=tmp_path) as temp_dir:
        search_dirs = [temp_dir]
        default_filename = "nonexistent.toml"
        default_config = {"fallback": "config"}

        # This should return the default config since the default filename doesn't exist
        config_files, config, from_defaults = handle_config(
            user_path=None,
            search_dirs=search_dirs,
            basenames=None,  # Using default_filename instead
            default_filename=default_filename,
            default_config=default_config,
        )

        # Should return None for config_files, the default config,
        # and True for from_defaults
        assert config_files is None
        assert config == default_config
        assert from_defaults is True
