import pytest

from docbuild.cli.cmd_cli import cli


@pytest.mark.skip("Replace --role with --env-config")
def test_verbosity_counts(context, fake_envfile, runner):
    mock = fake_envfile.mock
    result = runner.invoke(cli, ["--role=production", "-vv", "build"], obj=context)

    assert mock.call_count == 1
    assert result.exit_code == 0
    assert context.verbose == 2
