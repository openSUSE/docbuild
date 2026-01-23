from unittest.mock import MagicMock

import docbuild.config.load
from docbuild.config.load import load_and_merge_configs, load_single_config
from docbuild.constants import APP_CONFIG_FILENAME


def test_load_single_config_file(tmp_path):
    config_toml = """
    [server]
    name = "demo"
    """

    config_dir = tmp_path / "config1"
    config_dir.mkdir()
    config_file = config_dir / APP_CONFIG_FILENAME
    config_file.write_text(config_toml)

    config = load_single_config(config_file)

    assert config == {"server": {"name": "demo"}}


def test_load_multiple_config_files(tmp_path):
    config1 = """
    [server]
    name = "demo"
    debug = false
    """
    config2 = """
    [server]
    debug = true
    version = "1.0"
    """

    dir1 = tmp_path / "dir1"
    dir2 = tmp_path / "dir2"
    dir1.mkdir()
    dir2.mkdir()

    (dir1 / APP_CONFIG_FILENAME).write_text(config1)
    (dir2 / APP_CONFIG_FILENAME).write_text(config2)

    cfgfiles, config = load_and_merge_configs(
        [APP_CONFIG_FILENAME],
        dir1,
        dir2,
    )

    assert cfgfiles == (
        dir1 / APP_CONFIG_FILENAME,
        dir2 / APP_CONFIG_FILENAME,
    )
    assert config == {"server": {"name": "demo", "debug": True, "version": "1.0"}}


def test_load_config_with_default_paths(tmp_path):
    # Prepare a default config directory with the expected config file
    default_dir = tmp_path / "default_config"
    default_dir.mkdir()
    config_toml = """
    [app]
    default_used = true
    """
    (default_dir / APP_CONFIG_FILENAME).write_text(config_toml)

    cfgfiles, config = load_and_merge_configs(
        [APP_CONFIG_FILENAME],
        default_dir,
    )

    assert cfgfiles == (default_dir / APP_CONFIG_FILENAME,)
    assert config == {"app": {"default_used": True}}


def test_when_path_does_not_exist(monkeypatch):
    non_existing_path = "non_existing_dir"

    mock = MagicMock()
    mock.return_value = (tuple(), {})
    monkeypatch.setattr(docbuild.config.load, "load_and_merge_configs", mock)

    cfgfiles, config = load_and_merge_configs(
        [APP_CONFIG_FILENAME],
        non_existing_path,
    )

    assert cfgfiles == tuple()
    assert config == {}
