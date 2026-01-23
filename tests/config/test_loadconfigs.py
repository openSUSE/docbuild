import pytest

from docbuild.config.load import load_and_merge_configs
from docbuild.constants import APP_CONFIG_FILENAME, APP_NAME


def test_load_app_single_config(tmp_path):
    configpath = tmp_path / "etc" / APP_NAME
    configpath.mkdir(parents=True)
    (configpath / APP_CONFIG_FILENAME).write_text(
        """[server]
name = "localhost"
port = 1234
""",
    )

    cfgfiles, config = load_and_merge_configs([APP_CONFIG_FILENAME], configpath)
    assert cfgfiles == tuple([configpath / APP_CONFIG_FILENAME])
    assert config == {"server": {"name": "localhost", "port": 1234}}


def test_load_app_multiple_configs(tmp_path):
    system_path = tmp_path / "etc" / APP_NAME
    user_path = tmp_path / "home" / "test" / ".config" / APP_NAME
    local_path = tmp_path

    system_path.mkdir(parents=True)
    user_path.mkdir(parents=True)
    # local_path.mkdir(parents=True)

    (system_path / APP_CONFIG_FILENAME).write_text(
        """[server]
name = "localhost"
port = 1234
""",
    )
    (user_path / APP_CONFIG_FILENAME).write_text(
        """[server]
[db]
name = "mydatabase"
""",
    )
    (local_path / APP_CONFIG_FILENAME).write_text(
        """[server]
port = 4321""",
    )

    cfgfiles, config = load_and_merge_configs(
        [APP_CONFIG_FILENAME],
        system_path,
        user_path,
        local_path,
    )
    assert cfgfiles == (
        system_path / APP_CONFIG_FILENAME,
        user_path / APP_CONFIG_FILENAME,
        local_path / APP_CONFIG_FILENAME,
    )
    assert config == {
        "server": {"name": "localhost", "port": 4321},
        "db": {"name": "mydatabase"},
    }


def test_load_app_with_one_config_not_exists(tmp_path):
    system_path = tmp_path / "etc" / APP_NAME
    missing_path = tmp_path / "home" / "test" / ".config" / APP_NAME

    system_path.mkdir(parents=True)
    missing_path.mkdir(parents=True)

    (system_path / APP_CONFIG_FILENAME).write_text(
        """[server]
name = "localhost"
port = 1234
""",
    )

    cfgfiles, config = load_and_merge_configs(
        [APP_CONFIG_FILENAME],
        system_path,
        missing_path,
    )
    assert cfgfiles == (system_path / APP_CONFIG_FILENAME,)
    assert config == {"server": {"name": "localhost", "port": 1234}}


def test_load_app_with_empty_args(tmp_path):
    system_path = tmp_path / "etc" / APP_NAME

    system_path.mkdir(parents=True)

    (system_path / APP_CONFIG_FILENAME).write_text(
        """[server]
name = "localhost"
port = 1234
""",
    )
    cfgfiles, config = load_and_merge_configs(
        [APP_CONFIG_FILENAME],
        system_path,
    )
    assert cfgfiles == (system_path / APP_CONFIG_FILENAME,)
    assert config == {"server": {"name": "localhost", "port": 1234}}


def test_load_app_with_empty_paths(tmp_path):
    with pytest.raises(ValueError):
        load_and_merge_configs([APP_CONFIG_FILENAME])
