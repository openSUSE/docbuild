from docbuild.cli.cmd_cli import cli


def test_showconfig_help_option(runner):
    result = runner.invoke(cli, ['config', '--help'])
    # print(result.output)
    assert result.exit_code == 0
    assert 'Commands:' in result.output
    assert 'env' in result.output
