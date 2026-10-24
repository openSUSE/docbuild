"""Test verbosity handling."""

from pathlib import Path
from unittest.mock import Mock

import click
import pytest

import docbuild.cli.cmd_cli as cli_mod
from docbuild.cli.cmd_cli import cli
from docbuild.cli.context import DocBuildContext
from docbuild.models.config.app import AppConfig
from docbuild.models.config.env import EnvConfig


@pytest.fixture
def fake_handle_config(monkeypatch):
    """Fixture to mock the handle_config function behavior."""

    def _setup(resolver_func):
        monkeypatch.setattr(cli_mod, "handle_config", resolver_func)

    return _setup


@pytest.fixture(autouse=True)
def register_capture_command():
    """Register a temporary `capture` Click command for CLI invocation."""

    @click.command("capture")
    @click.pass_context
    def capture(ctx: click.Context) -> None:
        click.echo("capture")

    cli.add_command(capture)
    yield
    cli.commands.pop("capture", None)


@pytest.fixture
def mock_config_models(monkeypatch):
    """Mock AppConfig.from_dict and EnvConfig.from_dict to avoid real validation."""
    mock_logging_dump = Mock(return_value={"version": 1, "log_setup": True})
    mock_logging_attribute = Mock()
    mock_logging_attribute.model_dump = mock_logging_dump

    mock_app_instance = Mock(spec=AppConfig)
    mock_app_instance.logging = mock_logging_attribute

    mock_env_instance = Mock()
    mock_env_instance.paths.tmp.log_dir = Path("/tmp")

    mock_app_from_dict = Mock(return_value=mock_app_instance)
    mock_env_from_dict = Mock(return_value=mock_env_instance)

    monkeypatch.setattr(AppConfig, "from_dict", mock_app_from_dict)
    monkeypatch.setattr(EnvConfig, "from_dict", mock_env_from_dict)

    return {
        "app_instance": mock_app_instance,
        "env_instance": mock_env_instance,
    }


@pytest.mark.parametrize(
    "verbosity_flags, expected_verbose",
    [
        ([], 0),
        (["-v"], 1),
        (["-vv"], 2),
    ],
)
def test_verbosity_counts(
    runner,
    context: DocBuildContext,
    app_config_file,
    env_config_file,
    fake_handle_config,
    mock_config_models,
    verbosity_flags,
    expected_verbose,
):
    """Verify that the verbosity flags are correctly set in the context."""
    app_file, env_file = app_config_file, env_config_file

    def resolver(user_path, *args, **kwargs):
        if str(user_path) == str(app_file):
            return (app_file,), {"logging": {"version": 1}}, False
        if str(user_path) == str(env_file):
            return (env_file,), {"server": {"host": "1.2.3.4"}}, False
        return (None,), {}, True

    fake_handle_config(resolver)

    result = runner.invoke(
        cli,
        [
            *verbosity_flags,
            "--app-config",
            str(app_file),
            "--env-config",
            str(env_file),
            "capture",
        ],
        obj=context,
    )

    assert result.exit_code == 0
    assert context.verbose == expected_verbose
    assert "capture" in result.output
