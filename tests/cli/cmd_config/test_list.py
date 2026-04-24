from pathlib import Path
from unittest.mock import Mock

import pytest

from docbuild.cli.cmd_cli import cli
from docbuild.models.config.app import AppConfig
from docbuild.models.config.env import EnvConfig


@pytest.fixture
def mock_models(monkeypatch):
    """Local fixture to mock config models for list command tests."""
    mock_app = Mock(spec=AppConfig)
    # 1. Provide the logging attribute the CLI expects
    mock_app.logging = Mock()
    mock_app.logging.model_dump.return_value = {"version": 1}
    # 2. Provide the data for our 'list' command
    mock_app.model_dump.return_value = {"key": "value", "logging": {"level": "info"}}

    mock_env = Mock(spec=EnvConfig)
    mock_env.model_dump.return_value = {"env_key": "env_val"}

    monkeypatch.setattr(AppConfig, "from_dict", Mock(return_value=mock_app))
    monkeypatch.setattr(EnvConfig, "from_dict", Mock(return_value=mock_env))
    return mock_app

def test_config_list_json(runner, mock_models, fake_handle_config):
    """Test that config list shows the expected JSON output."""
    fake_handle_config(lambda *a, **k: ((Path("test.toml"),), {"key": "value"}, False))
    result = runner.invoke(cli, ["config", "list"])
    assert result.exit_code == 0
    assert '"key": "value"' in result.output

def test_config_list_flat(runner, mock_models, fake_handle_config):
    """Test that config list with --flat shows flattened keys."""
    fake_handle_config(lambda *a, **k: ((Path("test.toml"),), {"logging": {"level": "info"}}, False))
    result = runner.invoke(cli, ["config", "list", "--flat"])
    assert result.exit_code == 0
    assert "app.logging.level = info" in result.output
