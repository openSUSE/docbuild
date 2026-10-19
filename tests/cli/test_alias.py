"""Check the local alias group's registration, resolution and help behavior."""

import click
import pytest

from docbuild.cli.alias import AliasGroup


@pytest.mark.parametrize("aliases", ["ls", ("ls", "dir")])
@pytest.mark.parametrize("registration", ["decorator", "add_command"])
def test_alias_registration(runner, aliases, registration):
    group = AliasGroup(name="example")

    def callback():
        click.echo("listed")

    if registration == "decorator":
        command = group.command(name="list", aliases=aliases)(callback)
    else:
        command = click.command(name="original")(callback)
        group.add_command(command, name="list", aliases=aliases)

    ctx = click.Context(group)
    for name in ["list", *([aliases] if isinstance(aliases, str) else aliases)]:
        assert group.get_command(ctx, name) is command
        result = runner.invoke(group, [name])
        assert result.exit_code == 0
        assert result.output == "listed\n"
    result = runner.invoke(group, ["--help"])
    label = "list (ls)" if isinstance(aliases, str) else "list (dir, ls)"
    assert result.exit_code == 0
    assert label in result.output
    assert "original" not in result.output


@pytest.mark.parametrize("canonical_first", [False, True])
def test_canonical_command_wins(runner, canonical_first):
    group = AliasGroup(name="example")
    canonical = click.Command("ls", callback=lambda: click.echo("canonical"))
    listing = click.Command("list", callback=lambda: click.echo("listing"))
    if canonical_first:
        group.add_command(canonical)
    group.add_command(listing, aliases="ls")
    if not canonical_first:
        group.add_command(canonical)
    assert group.get_command(click.Context(group), "ls") is canonical
    result = runner.invoke(group, ["ls"])
    assert result.exit_code == 0
    assert result.output == "canonical\n"
    assert "list (ls)" not in runner.invoke(group, ["--help"]).output


def test_unknown_alias(runner):
    group = AliasGroup(name="example")
    group.add_command(click.Command("list"), aliases="ls")
    assert group.get_command(click.Context(group), "unknown") is None
    result = runner.invoke(group, ["unknown"])
    assert result.exit_code == 2
    assert "No such command 'unknown'" in result.output


def test_hidden_and_empty_help(runner):
    group = AliasGroup(name="example")
    assert "Commands:" not in runner.invoke(group, ["--help"]).output
    group.add_command(click.Command("secret", hidden=True), aliases="s")
    result = runner.invoke(group, ["--help"])
    assert result.exit_code == 0
    assert "secret" not in result.output
    assert "Commands:" not in result.output
