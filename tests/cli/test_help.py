import click
import pytest

from docbuild.cli.cmd_cli import cli


def collect_command_paths(
    cmd: click.Command,
    ctx: click.Context | None = None,
    prefix: list[str] | None = None,
) -> list[list[str]]:
    """Recursively discover all command/subcommand paths from Click."""
    prefix = prefix or []
    if ctx is None:
        ctx = click.Context(cmd)
    paths = [[*prefix, "--help"]]
    if isinstance(cmd, click.Group):
        for name in sorted(cmd.list_commands(ctx)):
            subcmd = cmd.get_command(ctx, name)
            if subcmd is not None:
                sub_ctx = click.Context(subcmd, parent=ctx, info_name=name)
                paths.extend(collect_command_paths(subcmd, sub_ctx, [*prefix, name]))
    return paths


def collect_all_commands(
    cmd: click.Command,
    ctx: click.Context | None = None,
    prefix: str = "",
) -> list[tuple[click.Command, str]]:
    """Recursively collect all Click Command objects with their full command names."""
    if ctx is None:
        ctx = click.Context(cmd)
    name = f"{prefix} {cmd.name}".strip() if cmd.name else "docbuild"
    commands = [(cmd, name)]
    if isinstance(cmd, click.Group):
        for sub_name in sorted(cmd.list_commands(ctx)):
            subcmd = cmd.get_command(ctx, sub_name)
            if subcmd is not None:
                sub_ctx = click.Context(subcmd, parent=ctx, info_name=sub_name)
                commands.extend(collect_all_commands(subcmd, sub_ctx, name))
    return commands


ALL_COMMAND_PATHS = collect_command_paths(cli)
ALL_COMMANDS = collect_all_commands(cli)


def test_help_option(runner):
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Usage:" in result.output
    # assert "-v" in result.output
    # assert "--version" in result.output
    # assert "-r" in result.output


@pytest.mark.parametrize(
    "subcommand_args",
    ALL_COMMAND_PATHS,
    ids=["_".join(p[:-1]) or "root" for p in ALL_COMMAND_PATHS],
)
def test_subcommand_help_no_param_leak(runner, subcommand_args):
    """Test that CLI help text does not leak developer docstrings."""
    result = runner.invoke(cli, subcommand_args)
    assert result.exit_code == 0
    assert ":param" not in result.output
    assert ":return" not in result.output


@pytest.mark.parametrize(
    "cmd,name",
    ALL_COMMANDS,
    ids=[name.replace(" ", "_") for _, name in ALL_COMMANDS],
)
def test_subcommand_docstring_has_formfeed_if_params(cmd, name):
    """Test that active help text and callback docstrings separate developer fields."""
    callback_doc = cmd.callback.__doc__ if cmd.callback else None
    assert callback_doc and callback_doc.strip(), (
        f"Click command '{name}' is missing a docstring."
    )

    active_help = cmd.help
    if active_help and any(k in active_help for k in (":param", ":return", ":raises")):
        assert "\f" in active_help, (
            f"Click command '{name}' has developer fields in its active help text "
            f"but is missing '\\f'."
        )

    if any(k in callback_doc for k in (":param", ":return", ":raises")):
        assert "\f" in callback_doc, (
            f"Click command '{name}' documents developer fields in its docstring "
            f"but is missing '\\f'."
        )
