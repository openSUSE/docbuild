"""Tests for creating configuration without requiring an existing setup."""

import os
from pathlib import Path
import tomllib
from unittest.mock import patch

import pytest

from docbuild.cli import cmd_cli
from docbuild.cli.cmd_cli import cli
from docbuild.cli.cmd_config import init as init_module
from docbuild.models.config.app import AppConfig
from docbuild.models.config.env import EnvConfig


@pytest.fixture(autouse=True)
def isolated_user_dirs(tmp_path, monkeypatch):
    """Keep tests away from the real user directories."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(home / ".local" / "state"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(home / ".cache"))
    return home


@pytest.fixture
def config_home(tmp_path, monkeypatch):
    directory = tmp_path / "userconfig" / "docbuild"
    monkeypatch.setattr(init_module, "CONFIG_HOME", directory)
    monkeypatch.setattr(cmd_cli, "CONFIG_PATHS", (directory,))
    monkeypatch.chdir(tmp_path)
    assert tmp_path in directory.parents
    return directory


@pytest.mark.parametrize(
    "flags, filenames",
    [
        ([], {"config.toml", "env.production.toml"}),
        (["--app"], {"config.toml"}),
        (["--env"], {"env.production.toml"}),
        (["--app", "--env"], {"config.toml", "env.production.toml"}),
    ],
    ids=["both-by-default", "app-only", "env-only", "both-explicit"],
)
def test_init_creates_selected_defaults(runner, config_home, flags, filenames):
    result = runner.invoke(cli, ["config", "init", *flags])

    assert result.exit_code == 0, result.output
    assert {path.name for path in config_home.iterdir()} == filenames
    for filename in filenames:
        content = (config_home / filename).read_text(encoding="utf-8")
        assert "Generated from Docbuild's built-in defaults" in content
        assert str(config_home / filename) in result.output
        assert "Used command: 'docbuild config init'" in content


def test_init_app_defaults(runner, config_home):
    result = runner.invoke(cli, ["config", "init", "--app"])
    assert result.exit_code == 0, result.output
    data = tomllib.loads((config_home / "config.toml").read_text())
    defaults = AppConfig.get_default_config()
    assert data["max_workers"] == defaults["max_workers"]
    assert (
        data["logging"]["handlers"]["console"]["class"]
        == defaults["logging"]["handlers"]["console"]["class"]
    )
    assert AppConfig.from_dict(data) == AppConfig.from_dict(defaults)


def test_init_env_defaults(runner, config_home):
    result = runner.invoke(cli, ["config", "init", "--env"])
    assert result.exit_code == 0, result.output
    data = tomllib.loads((config_home / "env.production.toml").read_text())
    defaults = EnvConfig.get_default_config(resolve_placeholders=False)
    assert data["paths"]["config_dir"] == defaults["paths"]["config_dir"]
    assert "{root_config_dir}" in data["paths"]["config_dir"]
    assert "{{dcfile}}" in data["build"]["daps"]["html"]
    assert "server" not in data["remote"]
    assert EnvConfig.from_dict(data) == EnvConfig.from_dict(defaults)


@pytest.mark.parametrize("flags", [[], ["--env"]])
@pytest.mark.parametrize(
    "role, expected",
    [("staging", "staging"), ("Prod", "production"), ("dev", "testing")],
)
def test_init_role(runner, config_home, flags, role, expected):
    result = runner.invoke(cli, ["config", "init", *flags, "--role", role])
    assert result.exit_code == 0, result.output
    filename = f"env.{expected}.toml"
    assert {path.name for path in config_home.iterdir()} == (
        {filename} if flags else {filename, "config.toml"}
    )
    data = tomllib.loads((config_home / filename).read_text())
    assert data["general"]["role"] == expected
    assert EnvConfig.from_dict(data).general.role.value == expected


@pytest.mark.parametrize(
    "flags, message",
    [
        (["--role", "invalid"], "Invalid value"),
        (["--app", "--role", "staging"], "--role only applies"),
        (["--app", "--env", "--role", "production"], "--role only applies"),
    ],
)
def test_init_rejects_invalid_role_options(runner, config_home, flags, message):
    result = runner.invoke(cli, ["config", "init", *flags])
    assert result.exit_code == 2
    assert message in result.output
    assert not config_home.exists()


@pytest.mark.parametrize("filename", ["config.toml", "env.production.toml"])
@pytest.mark.parametrize("kind", ["file", "directory", "symlink", "dangling-symlink"])
def test_init_never_overwrites_existing_paths(runner, config_home, filename, kind):
    config_home.mkdir(parents=True)
    destination = config_home / filename
    target = config_home.parent / "target.toml"
    if kind == "file":
        destination.write_text("my existing config", encoding="utf-8")
    elif kind == "directory":
        destination.mkdir()
    else:
        if kind == "symlink":
            target.write_text("keep this", encoding="utf-8")
        destination.symlink_to(target)

    result = runner.invoke(cli, ["config", "init"])

    assert result.exit_code != 0
    assert "Refusing to overwrite" in result.output
    assert str(destination) in result.output
    assert {path.name for path in config_home.iterdir()} == {filename}
    if kind == "file":
        assert destination.read_text(encoding="utf-8") == "my existing config"
    elif kind == "directory":
        assert destination.is_dir()
    else:
        assert destination.is_symlink()
        if kind == "symlink":
            assert target.read_text(encoding="utf-8") == "keep this"
        else:
            assert not target.exists()


def test_init_ignores_unselected_invalid_configuration(runner, config_home):
    config_home.mkdir(parents=True)
    existing = config_home / "config.toml"
    existing.write_text("not valid TOML [", encoding="utf-8")

    result = runner.invoke(cli, ["config", "init", "--env"])

    assert result.exit_code == 0, result.output
    assert existing.read_text(encoding="utf-8") == "not valid TOML ["
    assert (config_home / "env.production.toml").is_file()


def test_init_dry_run_does_not_create_directory(runner, config_home):
    result = runner.invoke(cli, ["--dry-run", "config", "init"])

    assert result.exit_code == 0, result.output
    assert result.output.count("Would create") == 2
    assert not config_home.exists()


def test_init_help_does_not_create_directory(runner, config_home):
    result = runner.invoke(cli, ["config", "init", "--help"])

    assert result.exit_code == 0, result.output
    assert "--app" in result.output
    assert "--env" in result.output
    assert not config_home.exists()


def test_init_reports_unwritable_directory(runner, config_home):
    parent = config_home.parent
    parent.mkdir(parents=True)
    parent.chmod(0o500)
    try:
        if os.access(parent, os.W_OK):
            pytest.skip(
                "Filesystem or user does not enforce directory write permissions"
            )
        result = runner.invoke(cli, ["config", "init", "--app"])
    finally:
        parent.chmod(0o700)

    assert result.exit_code != 0
    assert "Could not create" in result.output
    assert not config_home.exists()


def test_init_refuses_file_created_after_preflight(runner, config_home):
    original_open = Path.open

    def concurrent_open(path, mode="r", *args, **kwargs):
        if mode == "x":
            with original_open(path, "w", encoding="utf-8") as stream:
                stream.write("created by another process")
        return original_open(path, mode, *args, **kwargs)

    with patch.object(Path, "open", concurrent_open):
        result = runner.invoke(cli, ["config", "init", "--app"])

    assert result.exit_code != 0
    assert "Could not create" in result.output
    assert (config_home / "config.toml").read_text() == "created by another process"


def test_other_commands_still_validate_configuration(runner, config_home):
    config_home.mkdir(parents=True)
    (config_home / "config.toml").write_text("not valid TOML [", encoding="utf-8")

    result = runner.invoke(cli, ["config", "validate"])

    assert result.exit_code != 0


def test_default_app_config_is_independent():
    defaults = AppConfig.get_default_config()
    original_level = defaults["logging"]["root"]["level"]
    defaults["logging"]["root"]["level"] = "CUSTOM"
    assert AppConfig.get_default_config()["logging"]["root"]["level"] == original_level
