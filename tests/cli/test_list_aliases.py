"""Exercise list aliases through their parent groups and the CLI bootstrap."""

import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from lxml import etree
import pytest

from docbuild.cli import cmd_cli
from docbuild.cli.cmd_cache import cache
from docbuild.cli.cmd_config import config
from docbuild.cli.cmd_portal import cmd_list as portal_list, portal
from docbuild.cli.cmd_repo import repo
from docbuild.cli.context import DocBuildContext


@pytest.mark.parametrize("group", [cache, config, portal, repo])
def test_list_alias_help(runner, group):
    """Both spellings expose the same options and appear in group help."""
    canonical = runner.invoke(group, ["list", "--help"])
    alias = runner.invoke(group, ["ls", "--help"])
    assert canonical.exit_code == alias.exit_code == 0
    assert (
        canonical.output.replace(
            f"Usage: {group.name} list ", f"Usage: {group.name} ls ", 1
        )
        == alias.output
    )
    help_result = runner.invoke(group, ["--help"])
    assert help_result.exit_code == 0
    assert "list (ls)" in help_result.output


@pytest.mark.parametrize("name", ["list", "ls"])
def test_cache_list_alias(runner, tmp_path, name):
    """Cache aliases honor type filtering and show actual files."""
    meta = tmp_path / "meta"
    json = tmp_path / "json"
    json.mkdir()
    (json / "sample.json").write_text("{}")
    context = DocBuildContext()
    context.envconfig = SimpleNamespace(
        paths=SimpleNamespace(meta_cache_dir=meta, json_cache_dir=json)
    )
    result = runner.invoke(cache, [name, "--type", "json"], obj=context)
    assert result.exit_code == 0
    assert "sample.json" in result.output
    assert "Meta Cache" not in result.output


@pytest.mark.parametrize("name", ["list", "ls"])
def test_config_list_alias(runner, name):
    """Config aliases preserve raw and flat output options."""
    context = DocBuildContext()
    context.raw_appconfig = {"sample": "{placeholder}"}
    result = runner.invoke(
        config, [name, "--app", "--unresolved", "--flat"], obj=context
    )
    assert result.exit_code == 0
    assert "app.sample" in result.output
    assert "{placeholder}" in result.output


@pytest.mark.parametrize("name", ["list", "ls"])
def test_repo_list_alias(runner, tmp_path, name):
    """Repository aliases preserve failure and successful listing behavior."""
    context = DocBuildContext()
    directory = tmp_path / "repos"
    context.envconfig = SimpleNamespace(paths=SimpleNamespace(repo_dir=directory))
    result = runner.invoke(repo, [name], obj=context)
    assert result.exit_code == 1
    assert "No permanent repositories found" in result.output
    directory.mkdir()
    (directory / "sample").mkdir()
    result = runner.invoke(repo, [name], obj=context)
    assert result.exit_code == 0
    assert "sample" in result.output


@pytest.mark.parametrize("name", ["list", "ls"])
def test_portal_list_alias_invalid_doctype(runner, name):
    """Portal aliases use the same argument validation and exit code."""
    result = runner.invoke(
        portal, [name, "invalid_doctype_format!"], obj=DocBuildContext()
    )
    assert result.exit_code != 0
    assert "Error parsing doctype:" in result.output


@pytest.mark.parametrize("name", ["list", "ls"])
@pytest.mark.parametrize("validate", [False, True])
def test_config_alias_validation(runner, monkeypatch, name, validate):
    """CLI bootstrap skips validation for both names unless explicitly requested."""
    args = ["config", name, "--app", "--flat"]
    if validate:
        args.append("--validate")
    # Parsed Click arguments must work even when sys.argv is unrelated.
    monkeypatch.setattr(sys, "argv", ["docbuild", "unrelated"])
    context = DocBuildContext()
    context.raw_appconfig = {"sample": "value"}
    app_loader = MagicMock()
    env_loader = MagicMock()
    monkeypatch.setattr(cmd_cli, "load_app_config", app_loader)
    monkeypatch.setattr(cmd_cli, "load_env_config", env_loader)
    monkeypatch.setattr(cmd_cli, "setup_logging_from_context", MagicMock())
    result = runner.invoke(cmd_cli.cli, args, obj=context)
    assert result.exit_code == 0, result.output
    assert app_loader.call_args.args[-1] is (not validate)
    assert env_loader.call_args.args[-1] is (not validate)


@pytest.mark.parametrize("name", ["list", "ls"])
@pytest.mark.parametrize("validate", [False, True])
def test_config_alias_invalid_configuration(
    runner, monkeypatch, tmp_path, name, validate
):
    """Invalid config remains inspectable, while --validate rejects it."""
    monkeypatch.chdir(tmp_path)
    args = [
        "-C",
        "configx.canonical_url_domain=https://doc.example.net",
        "config",
        name,
        "--env",
        "--unresolved",
    ]
    if validate:
        args.append("--validate")
    monkeypatch.setattr(sys, "argv", ["docbuild", *args])
    result = runner.invoke(cmd_cli.cli, args)
    assert result.exit_code == (1 if validate else 0), result.output
    if validate:
        assert "Validation error in config file 'defaults':" in result.output
    else:
        assert "configx" in result.output


@pytest.mark.parametrize("name", ["list", "ls"])
def test_portal_list_alias_empty(runner, monkeypatch, tmp_path, name):
    """Portal aliases accept display options and report an empty portal."""
    context = DocBuildContext()
    context.envconfig = SimpleNamespace(
        paths=SimpleNamespace(main_portal_config=tmp_path / "portal.xml")
    )
    monkeypatch.setattr(
        portal_list,
        "parse_portal_config",
        AsyncMock(return_value=etree.fromstring(b"<portal/>")),
    )
    result = runner.invoke(portal, [name, "--flat", "--formats"], obj=context)
    assert result.exit_code == 0, result.output
    assert "No deliverables found matching the criteria." in result.output


@pytest.mark.parametrize("name", ["list", "ls"])
@pytest.mark.parametrize("validate", [False, True])
def test_config_alias_valid_configuration(
    runner, monkeypatch, tmp_path, name, validate
):
    """Both names load valid defaults with and without explicit validation."""
    monkeypatch.chdir(tmp_path)
    args = ["config", name, "--app", "--flat"]
    if validate:
        args.append("--validate")
    result = runner.invoke(cmd_cli.cli, args)
    assert result.exit_code == 0, result.output
    assert "app.max_workers" in result.output


@pytest.mark.parametrize("value", ["list", "ls"])
@pytest.mark.parametrize("option", ["--app-config", "--env-config"])
def test_config_validate_alias_option_value(
    runner, monkeypatch, tmp_path, value, option
):
    """An option value matching a list alias must not bypass validation."""
    monkeypatch.chdir(tmp_path)
    # Both files are valid TOML but invalid configuration for their model.
    content = (
        "[logging]\nversion = 2\n"
        if option == "--app-config"
        else "unknown_option = true\n"
    )
    (tmp_path / value).write_text(content)
    args = [option, value, "config", "validate"]
    monkeypatch.setattr(sys, "argv", ["docbuild", *args])
    result = runner.invoke(cmd_cli.cli, args)
    assert result.exit_code == 1, result.output
    if option == "--app-config":
        assert "Input should be 1" in result.output
    else:
        assert "unknown_option" in result.output
        assert "Extra inputs are not permitted" in result.output
    assert "Configuration is valid!" not in result.output
