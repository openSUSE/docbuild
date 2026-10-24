"""Integration tests for --set-app CLI option with config commands."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import docbuild.cli.cmd_cli as cmd_cli_module
from docbuild.cli.cmd_cli import cli, load_app_config
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


class TestSetAppWithLoadAppConfig:
    """Unit tests for --set-app option with load_app_config directly."""

    @pytest.mark.parametrize(
        "override,expected_path,expected_value",
        [
            ("max_workers=4", ["max_workers"], 4),
            ("max_workers=all", ["max_workers"], "all"),
            ("theme.preset=light", ["theme", "preset"], "light"),
        ],
    )
    def test_set_app_overrides_are_applied_to_raw_config(
        self, fake_handle_config, override, expected_path, expected_value
    ):
        """Test that --set-app overrides are correctly applied to raw_appconfig."""
        fake_handle_config(
            lambda *a, **k: ((Path("app.toml"),), {"max_workers": "half"}, False)
        )

        mock_ctx = MagicMock()
        mock_ctx.obj = DocBuildContext()

        load_app_config(
            mock_ctx,
            Path("app.toml"),
            max_workers=None,
            skip_validation=True,
            app_overrides=(override,),
        )

        raw = mock_ctx.obj.raw_appconfig
        current = raw
        for key in expected_path[:-1]:
            current = current[key]
        actual_value = current[expected_path[-1]]

        assert actual_value == expected_value

    @pytest.mark.parametrize(
        "override_pair,expected_final_value",
        [
            (("max_workers=4", "max_workers=8"), 8),
            (("theme.preset=dark", "theme.preset=light"), "light"),
        ],
    )
    def test_set_app_last_override_wins_real_values(
        self, fake_handle_config, override_pair, expected_final_value
    ):
        """Test that last override wins by checking actual config value."""
        fake_handle_config(
            lambda *a, **k: (
                (Path("app.toml"),),
                {"max_workers": "half", "theme": {}},
                False,
            )
        )

        mock_ctx = MagicMock()
        mock_ctx.obj = DocBuildContext()

        load_app_config(
            mock_ctx,
            Path("app.toml"),
            max_workers=None,
            skip_validation=True,
            app_overrides=override_pair,
        )

        raw = mock_ctx.obj.raw_appconfig

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

    def test_set_app_multiple_different_keys(self, fake_handle_config):
        """Test multiple overrides on different keys."""
        fake_handle_config(
            lambda *a, **k: (
                (Path("app.toml"),),
                {"max_workers": "half", "theme": {}},
                False,
            )
        )

        mock_ctx = MagicMock()
        mock_ctx.obj = DocBuildContext()

        load_app_config(
            mock_ctx,
            Path("app.toml"),
            max_workers=None,
            skip_validation=True,
            app_overrides=(
                "max_workers=4",
                "theme.preset=light",
            ),
        )

        raw = mock_ctx.obj.raw_appconfig

        assert raw["max_workers"] == 4
        assert raw["theme"]["preset"] == "light"

    def test_set_app_override_beats_workers_flag(self, fake_handle_config):
        """Test that -A wins over -j when both set max_workers."""
        fake_handle_config(
            lambda *a, **k: ((Path("app.toml"),), {"max_workers": "half"}, False)
        )

        mock_ctx = MagicMock()
        mock_ctx.obj = DocBuildContext()

        load_app_config(
            mock_ctx,
            Path("app.toml"),
            max_workers="2",
            skip_validation=True,
            app_overrides=("max_workers=8",),
        )

        assert mock_ctx.obj.raw_appconfig["max_workers"] == 8

    @pytest.mark.parametrize(
        "override",
        [
            r"theme.show\.edit\.link=1",
            "theme.'show.edit.link'=1",
            "theme.[show.edit.link]=2",
            'theme."show.edit.link"=3',
        ],
    )
    def test_set_app_dotted_keys_with_all_delimiters(
        self, fake_handle_config, override
    ):
        """Test that all delimiter and escape syntaxes produce correct config values."""
        fake_handle_config(lambda *a, **k: ((Path("app.toml"),), {"theme": {}}, False))

        mock_ctx = MagicMock()
        mock_ctx.obj = DocBuildContext()

        load_app_config(
            mock_ctx,
            Path("app.toml"),
            max_workers=None,
            skip_validation=True,
            app_overrides=(override,),
        )

        raw = mock_ctx.obj.raw_appconfig
        # All syntaxes should create: theme.show.edit.link
        expected_value = int(override.rsplit("=", 1)[1])
        assert raw["theme"]["show.edit.link"] == expected_value


class TestSetAppWithConfigCommands:
    """Integration tests for --set-app option with config validate command."""

    @patch.object(cmd_cli_module, "load_app_config")
    @patch.object(cmd_cli_module, "load_env_config")
    @patch.object(cmd_cli_module, "setup_logging")
    def test_set_app_option_reaches_load_app_config(
        self, mock_logging, mock_env, mock_app, runner
    ):
        """Test that -A overrides are passed through to load_app_config."""
        mock_ctx = MagicMock()
        mock_ctx.appconfigfiles = [Path("app.toml")]
        mock_ctx.envconfigfiles = [Path("env.toml")]
        mock_ctx.envconfig_from_defaults = False

        result = runner.invoke(
            cli,
            ["-A", "max_workers=4", "config", "validate"],
            obj=mock_ctx,
        )

        assert result.exit_code == 0
        assert "Configuration is valid" in result.output
        args, kwargs = mock_app.call_args
        app_overrides = kwargs.get("app_overrides", args[4] if len(args) > 4 else None)
        assert app_overrides == ("max_workers=4",)
