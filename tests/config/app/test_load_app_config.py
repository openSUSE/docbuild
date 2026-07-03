from docbuild.config.load import load_single_config
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
