from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

from docbuild.cli.cmd_cli import cli
from docbuild.cli.context import DocBuildContext
from docbuild.models.config.app import AppConfig
from docbuild.models.config.env import EnvConfig


@pytest.fixture
def mock_models(monkeypatch):
    """Local fixture to mock config models for validate command tests."""
    mock_app = Mock(spec=AppConfig)
    mock_app.logging = Mock()
    mock_app.logging.model_dump.return_value = {"version": 1}

    mock_env = Mock(spec=EnvConfig)

    monkeypatch.setattr(AppConfig, "from_dict", Mock(return_value=mock_app))
    monkeypatch.setattr(EnvConfig, "from_dict", Mock(return_value=mock_env))
    return mock_app

def test_config_validate_success(runner, mock_models, fake_handle_config):
    """Test that config validate succeeds with valid configuration."""
    # Setup context attributes so they don't default to Mocks
    # Manually create the context with real lists/tuples to avoid Mock iteration errors
    ctx_obj = DocBuildContext()
    ctx_obj.appconfig = mock_models
    ctx_obj.appconfigfiles = (Path("app.toml"),)
    ctx_obj.envconfig = MagicMock() # Mock for EnvConfig
    ctx_obj.envconfigfiles = (Path("env.toml"),)
    ctx_obj.doctypes = [] # Explicitly empty list

    fake_handle_config(lambda *a, **k: ((Path("app.toml"),), {"key": "val"}, False))

    # We use 'standalone_mode=False' so we can see the actual error if it crashes
    result = runner.invoke(cli, ["config", "validate"], obj=ctx_obj)

    assert result.exit_code == 0
    # Use 'in' to check for text without worrying about exact formatting/colors
    assert "Configuration is valid" in result.output
    assert "Application Configuration" in result.output
