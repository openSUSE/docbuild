"""Tests for shell completion of doctypes."""

from collections.abc import Iterator
from pathlib import Path
from unittest.mock import patch

import click
from click.testing import CliRunner
from lxml import etree  # type: ignore
import pytest

from docbuild.cli import completion
from docbuild.cli.cmd_cli import cli
from docbuild.cli.completion import (
    collect_docsets,
    complete_doctypes,
    load_portal_tree,
)

PORTAL_XML = """<?xml version="1.0" encoding="UTF-8"?>
<portal schemaversion="7.0">
  <product xml:id="sles">
    <docset path="15-SP7" lifecycle="supported">
      <resources>
        <locale lang="en-us">
          <deliverable xml:id="admin_guide"><dc file="DC-admin"/></deliverable>
        </locale>
      </resources>
    </docset>
    <docset path="16.0" lifecycle="supported">
      <resources>
        <locale lang="en-us">
          <deliverable xml:id="install_guide"><dc file="DC-install"/></deliverable>
        </locale>
      </resources>
    </docset>
  </product>
</portal>
"""

PARAM = click.Argument(["doctypes"], nargs=-1)


def values(items: list) -> list[str]:
    """Return the plain values of completion items."""
    return [item.value for item in items]


def make_ctx(**params: object) -> click.Context:
    """Create a root context carrying the given parameters."""
    ctx = click.Context(click.Command("docbuild"))
    ctx.params = dict(params)
    return ctx


@pytest.fixture
def portal_tree() -> etree._Element:
    """Return a parsed portal config with two SLES docsets."""
    return etree.fromstring(PORTAL_XML.encode("utf-8"))


def test_collect_docsets(portal_tree) -> None:
    assert collect_docsets(portal_tree, "sles") == {"15-SP7", "16.0"}


def test_complete_products() -> None:
    result = values(complete_doctypes(make_ctx(), PARAM, "sl"))

    assert "sles" in result
    assert "sled" in result
    assert all(value.startswith("sl") for value in result)


def test_complete_products_excludes_wildcard() -> None:
    assert "*" not in values(complete_doctypes(make_ctx(), PARAM, ""))


def test_complete_docsets_from_portal_config(portal_tree) -> None:
    with patch.object(completion, "load_portal_tree", return_value=portal_tree):
        result = values(complete_doctypes(make_ctx(), PARAM, "sles/"))

    assert result == ["sles/*", "sles/15-SP7", "sles/16.0"]


def test_complete_docsets_filters_by_prefix(portal_tree) -> None:
    with patch.object(completion, "load_portal_tree", return_value=portal_tree):
        result = values(complete_doctypes(make_ctx(), PARAM, "sles/1"))

    assert result == ["sles/15-SP7", "sles/16.0"]


def test_complete_docsets_comma_separated(portal_tree) -> None:
    with patch.object(completion, "load_portal_tree", return_value=portal_tree):
        result = values(complete_doctypes(make_ctx(), PARAM, "sles/16.0,1"))

    assert result == ["sles/16.0,15-SP7"]


def test_complete_docsets_without_portal_config() -> None:
    with patch.object(completion, "load_portal_tree", return_value=None):
        result = values(complete_doctypes(make_ctx(), PARAM, "sles/"))

    assert result == ["sles/*"]


def test_complete_docsets_unknown_product(portal_tree) -> None:
    with patch.object(completion, "load_portal_tree", return_value=portal_tree):
        result = values(complete_doctypes(make_ctx(), PARAM, "bogus/"))

    assert result == ["bogus/*"]


def test_complete_docsets_wildcard_product_skips_portal_config() -> None:
    with patch.object(completion, "load_portal_tree") as mock_load:
        result = values(complete_doctypes(make_ctx(), PARAM, "*/"))

    mock_load.assert_not_called()
    assert result == ["*/*"]


def test_complete_languages() -> None:
    result = values(complete_doctypes(make_ctx(), PARAM, "sles/16.0/de"))

    assert result == ["sles/16.0/de-de"]


def test_complete_languages_comma_separated() -> None:
    result = values(complete_doctypes(make_ctx(), PARAM, "sles/16.0/de-de,"))

    assert "sles/16.0/de-de,en-us" in result
    assert "sles/16.0/de-de,de-de" not in result


def test_complete_too_many_segments() -> None:
    assert complete_doctypes(make_ctx(), PARAM, "sles/16.0/en-us/x") == []


def test_load_portal_tree_from_env_override(tmp_path: Path) -> None:
    portal = tmp_path / "portal.xml"
    portal.write_text(PORTAL_XML, encoding="utf-8")
    ctx = make_ctx(env_overrides=(f"paths.main_portal_config={portal}",))

    tree = load_portal_tree(ctx)

    assert tree is not None
    assert collect_docsets(tree, "sles") == {"15-SP7", "16.0"}


def test_load_portal_tree_missing_file_returns_none(tmp_path: Path) -> None:
    missing = tmp_path / "missing.xml"
    ctx = make_ctx(env_overrides=(f"paths.main_portal_config={missing}",))

    assert load_portal_tree(ctx) is None


def iter_doctypes_params(
    group: click.Group, path: str = ""
) -> Iterator[tuple[str, click.Parameter]]:
    """Yield (command path, parameter) for every DOCTYPES argument."""
    for name, command in group.commands.items():
        if isinstance(command, click.Group):
            yield from iter_doctypes_params(command, f"{path}{name} ")
            continue
        for param in command.params:
            if param.name == "doctypes":
                yield f"{path}{name}", param


def test_every_doctypes_argument_completes() -> None:
    params = list(iter_doctypes_params(cli))

    assert params, "no DOCTYPES arguments found"
    for path, param in params:
        assert param._custom_shell_complete is complete_doctypes, path


@pytest.mark.parametrize(
    ("shell", "marker"),
    [
        ("bash", "_docbuild_completion()"),
        ("zsh", "#compdef docbuild"),
        ("fish", "complete --no-files --command docbuild"),
    ],
)
def test_shell_source_script(shell: str, marker: str) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        prog_name="docbuild",
        env={"_DOCBUILD_COMPLETE": f"{shell}_source"},
    )

    assert result.exit_code == 0, result.output
    assert marker in result.output


def test_bash_completes_doctypes_end_to_end(tmp_path: Path) -> None:
    portal = tmp_path / "portal.xml"
    portal.write_text(PORTAL_XML, encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        prog_name="docbuild",
        env={
            "_DOCBUILD_COMPLETE": "bash_complete",
            "COMP_WORDS": f"docbuild -C paths.main_portal_config={portal} portal list sles/",
            "COMP_CWORD": "5",
        },
    )

    assert result.exit_code == 0, result.output
    assert result.output.splitlines() == [
        "plain,sles/*",
        "plain,sles/15-SP7",
        "plain,sles/16.0",
    ]
