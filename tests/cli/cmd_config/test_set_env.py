"""Integration tests for --set-env CLI option with config commands."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import docbuild.cli.cmd_cli as cmd_cli_module
from docbuild.cli.cmd_cli import cli, load_env_config
from docbuild.cli.context import DocBuildContext


@pytest.fixture
def runner():
    """Provide a Click test runner."""
    from click.testing import CliRunner
    return CliRunner()


@pytest.fixture
def fake_handle_config(monkeypatch):
    """Fixture to mock the handle_config function behavior."""
    def _setup(resolver_func):
        monkeypatch.setattr(cmd_cli_module, "handle_config", resolver_func)
    return _setup


class TestSetEnvWithLoadEnvConfig:
    """Unit tests for --set-env option with load_env_config directly."""

    @pytest.mark.parametrize(
        "override,expected_path,expected_value",
        [
            ("general.role=production", ["general", "role"], "production"),
            ("general.role=staging", ["general", "role"], "staging"),
            ("general.role=test", ["general", "role"], "test"),
            ("server.port=8080", ["server", "port"], 8080),
            ("server.port=9000", ["server", "port"], 9000),
        ],
    )
    def test_set_env_overrides_are_applied_to_raw_config(
        self, fake_handle_config, override, expected_path, expected_value
    ):
        """Test that --set-env overrides are correctly applied to raw_envconfig."""
        fake_handle_config(
            lambda *a, **k: ((Path("env.toml"),), {"general": {"role": "devel"}}, False)
        )

        mock_ctx = MagicMock()
        mock_ctx.obj = DocBuildContext()

        load_env_config(
            mock_ctx, Path("env.toml"), env_overrides=(override,), skip_validation=True
        )

        raw = mock_ctx.obj.raw_envconfig
        current = raw
        for key in expected_path[:-1]:
            current = current[key]
        actual_value = current[expected_path[-1]]

        assert actual_value == expected_value

    @pytest.mark.parametrize(
        "override_pair,expected_final_value",
        [
            (("server.port=8080", "server.port=9000"), 9000),
            (("general.role=staging", "general.role=production"), "production"),
            (("xslt.html.'show.edit.link'=0", "xslt.html.'show.edit.link'=1"), 1),
        ],
    )
    def test_set_env_last_override_wins_real_values(
        self, fake_handle_config, override_pair, expected_final_value
    ):
        """Test that last override wins by checking actual config value."""
        fake_handle_config(
            lambda *a, **k: (
                (Path("env.toml"),),
                {"general": {"role": "devel"}, "server": {"port": 5000}, "xslt": {"html": {}}},
                False,
            )
        )

        mock_ctx = MagicMock()
        mock_ctx.obj = DocBuildContext()

        load_env_config(
            mock_ctx, Path("env.toml"), env_overrides=override_pair, skip_validation=True
        )

        raw = mock_ctx.obj.raw_envconfig

        # Extract the expected key path from the last override
        last_override = override_pair[-1]
        key_part, _ = last_override.split("=")

        # Navigate to the value
        keys = cmd_cli_module.parse_key(key_part)
        current = raw
        for key in keys[:-1]:
            current = current[key]
        actual_value = current[keys[-1]]

        assert actual_value == expected_final_value

    def test_set_env_multiple_different_keys(self, fake_handle_config):
        """Test multiple overrides on different keys."""
        fake_handle_config(
            lambda *a, **k: (
                (Path("env.toml"),),
                {"general": {"role": "devel", "name": "default"}, "server": {"port": 5000}},
                False,
            )
        )

        mock_ctx = MagicMock()
        mock_ctx.obj = DocBuildContext()

        load_env_config(
            mock_ctx,
            Path("env.toml"),
            env_overrides=(
                "general.role=production",
                "general.name=custom-env",
                "server.port=8080",
            ),
            skip_validation=True,
        )

        raw = mock_ctx.obj.raw_envconfig

        assert raw["general"]["role"] == "production"
        assert raw["general"]["name"] == "custom-env"
        assert raw["server"]["port"] == 8080

    @pytest.mark.parametrize(
        "override",
        [
            "xslt.html.'show.edit.link'=1",
            "xslt.html.[show.edit.link]=2",
            'xslt.html."show.edit.link"=3',
        ],
    )
    def test_set_env_dotted_keys_with_all_delimiters(
        self, fake_handle_config, override
    ):
        """Test that all three delimiter syntaxes produce correct config values."""
        fake_handle_config(
            lambda *a, **k: ((Path("env.toml"),), {"xslt": {"html": {}}}, False)
        )

        mock_ctx = MagicMock()
        mock_ctx.obj = DocBuildContext()

        load_env_config(
            mock_ctx, Path("env.toml"), env_overrides=(override,), skip_validation=True
        )

        raw = mock_ctx.obj.raw_envconfig
        # All three syntaxes should create: xslt.html.show.edit.link
        expected_value = int(override.rsplit("=", 1)[1])
        assert raw["xslt"]["html"]["show.edit.link"] == expected_value


class TestSetEnvWithConfigCommands:
    """Integration tests for --set-env option with config validate command."""

    @patch.object(cmd_cli_module, "load_app_config")
    @patch.object(cmd_cli_module, "load_env_config")
    @patch.object(cmd_cli_module, "setup_logging")
    @pytest.mark.parametrize(
        "override",
        [
            "general.role=production",
            "general.role=staging",
            "general.role=test",
        ],
    )
    def test_set_env_valid_enum_with_config_validate(
        self, mock_logging, mock_env, mock_app, runner, override
    ):
        """Test --set-env with valid enum value and 'config validate'."""
        mock_ctx = MagicMock()
        mock_ctx.appconfigfiles = [Path("app.toml")]
        mock_ctx.envconfigfiles = [Path("env.toml")]
        mock_ctx.envconfig_from_defaults = False

        result = runner.invoke(
            cli,
            ["-C", override, "config", "validate"],
            obj=mock_ctx,
        )

        # Should pass validation
        assert result.exit_code == 0
        assert "Configuration is valid" in result.output



    @patch.object(cmd_cli_module, "load_app_config")
    @patch.object(cmd_cli_module, "load_env_config")
    @patch.object(cmd_cli_module, "setup_logging")
    @pytest.mark.parametrize(
        "override",
        [
            "xslt.html.'show.edit.link'=1",
            "xslt.html.[show.edit.link]=1",
            'xslt.html."show.edit.link"=1',
        ],
    )
    def test_set_env_dotted_keys_with_delimiters(
        self, mock_logging, mock_env, mock_app, runner, override
    ):
        """Test that dotted keys work with all three delimiter syntaxes."""
        mock_ctx = MagicMock()
        mock_ctx.appconfigfiles = [Path("app.toml")]
        mock_ctx.envconfigfiles = [Path("env.toml")]
        mock_ctx.envconfig_from_defaults = False

        result = runner.invoke(
            cli,
            ["-C", override, "config", "validate"],
            obj=mock_ctx,
        )

        # All three syntax variants should be accepted
        assert result.exit_code == 0
        assert "Configuration is valid" in result.output
