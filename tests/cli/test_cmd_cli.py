"""Tests for the main CLI entry point and configuration loading flow."""

from pathlib import Path
from unittest.mock import Mock, patch

import click
from pydantic import ValidationError
import pytest

import docbuild.cli.cmd_cli as cli_mod
from docbuild.cli.context import DocBuildContext
from docbuild.models.config.app import AppConfig
from docbuild.models.config.env import EnvConfig
from docbuild.utils.pidlock import LockAcquisitionError

cli = cli_mod.cli


@pytest.fixture
def fake_handle_config(monkeypatch):
    """Fixture to mock the handle_config function behavior.
    This allows us to simulate different filesystem states (finding/not finding configs)
    without actual IO.
    """
    def _setup(resolver_func):
        monkeypatch.setattr(cli_mod, "handle_config", resolver_func)
    return _setup


@pytest.fixture(autouse=True)
def register_capture_command():
    """Autouse fixture to register a temporary `capture` Click command.

    The command is removed after each test to avoid leaking state.
    """
    @click.command("capture")
    @click.pass_context
    def capture(ctx: click.Context) -> None:
        click.echo("capture")

    cli.add_command(capture)
    yield
    cli.commands.pop("capture", None)


@pytest.fixture
def mock_config_models(monkeypatch):
    """Fixture to mock AppConfig.from_dict and EnvConfig.from_dict.

    Ensures the mock AppConfig instance has the necessary
    logging attributes and methods that the CLI calls during setup.
    """
    # Mock the nested logging attribute and its model_dump method
    mock_logging_dump = Mock(return_value={"version": 1, "log_setup": True})
    mock_logging_attribute = Mock()
    mock_logging_attribute.model_dump = mock_logging_dump

    # Create simple mock Pydantic objects
    mock_app_instance = Mock(spec=AppConfig)
    mock_app_instance.logging = mock_logging_attribute

    mock_env_dump = Mock(return_value={"env_data": "from_mock_dump"})
    mock_env_instance = Mock(spec=EnvConfig)
    mock_env_instance.model_dump.return_value = mock_env_dump

    # Mock the static methods that perform validation
    mock_app_from_dict = Mock(return_value=mock_app_instance)
    mock_env_from_dict = Mock(return_value=mock_env_instance)

    # Patch the actual classes
    monkeypatch.setattr(AppConfig, "from_dict", mock_app_from_dict)
    monkeypatch.setattr(EnvConfig, "from_dict", mock_env_from_dict)

    return {
        "app_instance": mock_app_instance,
        "env_instance": mock_env_instance,
        "app_from_dict": mock_app_from_dict,
        "env_from_dict": mock_env_from_dict,
    }


# --- Tests focused on CLI flow and coverage ---

def test_cli_no_subcommand_shows_help(runner):
    """Verify that calling docbuild without a command shows help.
    Covers the 'if ctx.invoked_subcommand is None' block.
    """
    result = runner.invoke(cli)
    assert result.exit_code == 0
    assert "Main CLI tool for document operations" in result.output
    assert "----------" in result.output


def test_cli_defaults(
    runner,
    app_config_file,
    fake_handle_config,
    mock_config_models,
):
    """Test standard execution flow with default config handling."""
    app_file = app_config_file

    def resolver(user_path, *args, **kwargs):
        if user_path == app_file:
            return (user_path,), {"logging": {"version": 1}}, False
        return (Path("default_env.toml"),), {"env_data": "from_default"}, True

    fake_handle_config(resolver)
    context = DocBuildContext()

    result = runner.invoke(
        cli,
        ["--app-config", str(app_file), "capture"],
        obj=context,
    )

    assert result.exit_code == 0
    assert "capture" in result.output
    assert context.appconfig_from_defaults is False
    assert context.envconfig_from_defaults is True


def test_cli_with_app_and_env_config(
    runner,
    app_config_file,
    env_config_file,
    fake_handle_config,
    mock_config_models,
):
    """Test execution when both config files are explicitly provided."""
    app_file, env_file = app_config_file, env_config_file

    def resolver(user_path, *args, **kwargs):
        if str(user_path) == str(app_file):
            return (app_file,), {"logging": {"version": 1}}, False
        if str(user_path) == str(env_file):
            return (env_file,), {"server": {"host": "1.2.3.4"}}, False
        return (None,), {}, True

    fake_handle_config(resolver)

    context = DocBuildContext()
    result = runner.invoke(
        cli,
        ["--app-config", str(app_file), "--env-config", str(env_file), "capture"],
        obj=context,
    )

    assert result.exit_code == 0
    assert context.envconfigfiles == (env_file,)


@pytest.mark.parametrize("is_app_config_failure", [True, False])
def test_cli_config_validation_failure(
    monkeypatch,
    runner,
    fake_handle_config,
    mock_config_models,
    is_app_config_failure,
):
    """Verify that the CLI handles Pydantic ValidationErrors with the custom formatter."""
    mock_validation_error = ValidationError.from_exception_data(
        "TestModel",
        [{"type": "int_parsing", "loc": ("server", "port"), "input": "x"}]
    )

    if is_app_config_failure:
        mock_config_models["app_from_dict"].side_effect = mock_validation_error
    else:
        mock_config_models["env_from_dict"].side_effect = mock_validation_error

    fake_handle_config(lambda *a, **k: ((Path("test.toml"),), {"x": 1}, False))

    result = runner.invoke(cli, ["capture"])
    assert result.exit_code == 1
    assert "Validation error" in result.output
    assert "server.port" in result.output


@pytest.mark.parametrize("model_target", ["AppConfig", "EnvConfig"])
def test_cli_generic_value_error(
    monkeypatch,
    runner,
    mock_config_models,
    fake_handle_config,
    model_target,
):
    """Verify handling of generic ValueErrors (non-Pydantic) in the loading phase."""
    mock_log_error = Mock()
    monkeypatch.setattr(cli_mod.log, "error", mock_log_error)

    if model_target == "AppConfig":
        mock_config_models["app_from_dict"].side_effect = ValueError("Generic App Error")
    else:
        mock_config_models["env_from_dict"].side_effect = ValueError("Generic Env Error")

    fake_handle_config(lambda *a, **k: ((Path("test.toml"),), {"x": 1}, False))

    result = runner.invoke(cli, ["capture"])
    assert result.exit_code == 1
    assert mock_log_error.called


def test_cli_lock_acquisition_failure(
    monkeypatch,
    runner,
    mock_config_models,
    fake_handle_config,
):
    """Verify the CLI exits correctly when a PID lock cannot be acquired."""
    mock_log_error = Mock()
    monkeypatch.setattr(cli_mod.log, "error", mock_log_error)

    # Return a path so the lock logic triggers
    fake_handle_config(lambda *a, **k: ((Path("env.toml"),), {"s": "t"}, False))

    with patch("docbuild.cli.cmd_cli.PidFileLock") as mock_lock:
        mock_lock.return_value.__enter__.side_effect = LockAcquisitionError("Lock busy")

        result = runner.invoke(cli, ["capture"])
        assert result.exit_code == 1
        mock_log_error.assert_any_call("Lock busy")


def test_cli_general_lock_exception(
    monkeypatch,
    runner,
    mock_config_models,
    fake_handle_config,
):
    """Verify handling of unexpected exceptions during the locking phase."""
    mock_log_error = Mock()
    monkeypatch.setattr(cli_mod.log, "error", mock_log_error)

    fake_handle_config(lambda *a, **k: ((Path("env.toml"),), {"s": "t"}, False))

    with patch("docbuild.cli.cmd_cli.PidFileLock") as mock_lock:
        mock_lock.return_value.__enter__.side_effect = Exception("System Crash")

        result = runner.invoke(cli, ["capture"])
        assert result.exit_code == 1
        assert any("Failed to set up environment lock" in str(arg)
                   for arg, kw in mock_log_error.call_args_list)


def test_cli_verbose_and_debug(
    runner,
    app_config_file,
    fake_handle_config,
    mock_config_models,
):
    """Verify that verbosity and debug flags are correctly set in the context."""
    app_file = app_config_file

    def resolver(user_path, *args, **kwargs):
        return (app_file,), {"logging": {"version": 1}}, False

    fake_handle_config(resolver)
    context = DocBuildContext()

    result = runner.invoke(
        cli,
        ["-vvv", "--debug", "--app-config", str(app_file), "capture"],
        obj=context,
    )

    assert result.exit_code == 0
    assert context.verbose == 3
    assert context.debug is True
