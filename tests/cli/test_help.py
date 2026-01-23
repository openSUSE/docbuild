from docbuild.cli.cmd_cli import cli


def test_help_option(runner):
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Usage:" in result.output
    # assert "-v" in result.output
    # assert "--version" in result.output
    # assert "-r" in result.output
